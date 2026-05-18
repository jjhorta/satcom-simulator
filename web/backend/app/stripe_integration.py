"""
web/backend/app/stripe_integration.py — Stripe Checkout + Webhook handling.

Billing is org-level. The Stripe Customer object is attached to the organization,
not the individual user. When a subscription changes, the webhook:
  1. Updates organizations.subscription_tier
  2. Promotes org members to the max role allowed by the new tier

Environment variables (in .env):
  STRIPE_SECRET_KEY       sk_live_... or sk_test_...
  STRIPE_WEBHOOK_SECRET   whsec_... (for signature verification)
  STRIPE_PRICE_PRO        price_xxx (monthly)
  STRIPE_PRICE_PRO_YEAR   price_xxx (annual)
  STRIPE_PRICE_ENT        price_xxx (enterprise monthly)
  STRIPE_PRICE_ENT_YEAR   price_xxx (enterprise annual)
  APP_URL                 https://constellation-sim.example.com
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import sqlite3
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from stripe import StripeError

from .auth import get_current_user
from .config import Settings, get_settings
from .db import _get_db_path, get_organization, mark_stripe_event
from .deps import require_permission
from .tier_config import get_limits, role_max_from_subscription

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ── Helpers ─────────────────────────────────────────────────────────────────


def setup_stripe(settings: Settings) -> None:
    """Configure Stripe SDK with the secret key."""
    stripe.api_key = settings.stripe_secret_key


def _get_org_by_stripe_customer(
    outputs_dir: Any, customer_id: str
) -> dict | None:
    """Look up an organization by its Stripe customer ID."""
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM organizations WHERE stripe_customer_id = ?",
        (customer_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _update_org_subscription(
    outputs_dir: Any,
    org_id: int,
    tier: str,
    status: str,
    sub_id: str | None = None,
) -> None:
    """Update an organization's subscription fields."""
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """UPDATE organizations
           SET subscription_tier = ?,
               subscription_status = ?,
               subscription_updated_at = ?,
               stripe_subscription_id = COALESCE(?, stripe_subscription_id)
           WHERE id = ?""",
        (tier, status, now, sub_id, org_id),
    )
    conn.commit()
    conn.close()


def _promote_org_members_to_max_role(
    outputs_dir: Any, org_id: int, allowed_role: str
) -> None:
    """Promote members up to the max role their subscription allows.

    Never demotes anyone — if a member is already at a higher role,
    they stay where they are.
    """
    rank = {"viewer": 0, "demo": 1, "creator": 2, "team_manager": 3, "admin": 4}
    target_level = rank.get(allowed_role, 0)

    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.row_factory = sqlite3.Row
    members = conn.execute(
        "SELECT id, role FROM users WHERE org_id = ?", (org_id,)
    ).fetchall()

    for m in members:
        current_level = rank.get(m["role"], 0)
        if target_level > current_level:
            conn.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (allowed_role, m["id"]),
            )
    conn.commit()
    conn.close()


def _price_id_to_tier(price_id: str, settings: Settings) -> str:
    """Map a Stripe Price ID to a subscription tier name."""
    mapping = {
        settings.stripe_price_pro: "pro",
        settings.stripe_price_pro_year: "pro",
        settings.stripe_price_ent: "enterprise",
        settings.stripe_price_ent_year: "enterprise",
    }
    return mapping.get(price_id, "free")


# ── Checkout Session ────────────────────────────────────────────────────────


@router.post("/create-checkout")
async def create_checkout(
    price_id: str,
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("billing:manage")),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Create a Stripe Checkout Session for the user's organization.

    The checkout is linked to the org via metadata.org_id.
    After payment, the webhook looks up the org by stripe_customer_id.
    """
    setup_stripe(settings)

    org = get_organization(settings.outputs_dir, user.get("org_id"))
    if not org:
        raise HTTPException(status_code=400, detail="No organization found")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=user.get("email"),
            client_reference_id=str(org["id"]),
            success_url=f"{settings.app_url}/billing?success=true",
            cancel_url=f"{settings.app_url}/billing?canceled=true",
            metadata={
                "org_id": str(org["id"]),
                "org_name": org["name"],
            },
            allow_promotion_codes=True,
            tax_id_collection={"enabled": True},
        )
        return {"url": session.url}
    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Customer Portal (manage subscription) ───────────────────────────────────


@router.get("/portal")
async def billing_portal(
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("billing:manage")),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Return a Stripe Customer Portal URL for managing the org subscription."""
    setup_stripe(settings)
    org = get_organization(settings.outputs_dir, user.get("org_id"))
    if not org or not org.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No active subscription")

    try:
        session = stripe.billing_portal.Session.create(
            customer=org["stripe_customer_id"],
            return_url=f"{settings.app_url}/billing",
        )
        return {"url": session.url}
    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Current subscription info ───────────────────────────────────────────────


@router.get("/subscription")
async def get_subscription(
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Return current subscription info for the user's organization."""
    org = get_organization(settings.outputs_dir, user.get("org_id"))
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    limits = get_limits(user.get("role", "viewer"))

    return {
        "tier": org.get("subscription_tier", "free"),
        "subscription_status": org.get("subscription_status", "inactive"),
        "org_id": org["id"],
        "org_name": org["name"],
        "role": user.get("role", "viewer"),
        "jobs_used": user.get("jobs_used_this_month", 0),
        "jobs_limit": limits.get("jobs_per_month", 0),
        "jobs_remaining": (
            -1
            if limits.get("jobs_per_month", 0) == -1
            else max(0, limits["jobs_per_month"] - user.get("jobs_used_this_month", 0))
        ),
        "demo_jobs_remaining": (
            max(0, user.get("demo_jobs_limit", 0) - user.get("demo_jobs_used", 0))
            if user.get("role") == "demo"
            else None
        ),
    }


# ── Webhook ─────────────────────────────────────────────────────────────────


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    """
    Stripe webhook endpoint — receives subscription lifecycle events.

    Required events in Stripe Dashboard:
      - customer.subscription.created
      - customer.subscription.updated
      - customer.subscription.deleted
      - invoice.payment_succeeded
      - invoice.payment_failed
    """
    setup_stripe(settings)

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Idempotency check — skip if already processed
    if not mark_stripe_event(
        settings.outputs_dir, event.id, event.type, json.dumps(event.data)
    ):
        return JSONResponse(content={"status": "duplicate"}, status_code=200)

    handler = _EVENT_HANDLERS.get(event.type)
    if handler:
        handler(event.data, settings)

    return JSONResponse(content={"status": "ok"}, status_code=200)


# ── Webhook Event Handlers ──────────────────────────────────────────────────


def _handle_subscription_created(data: dict, settings: Settings) -> None:
    """New subscription: link org to Stripe customer, upgrade tier."""
    sub: dict = data["object"]
    customer_id: str = sub["customer"]
    price_id: str = sub["items"]["data"][0]["price"]["id"]
    tier: str = _price_id_to_tier(price_id, settings)
    metadata: dict = sub.get("metadata", {})
    org_id = metadata.get("org_id")

    if not org_id:
        org = _get_org_by_stripe_customer(settings.outputs_dir, customer_id)
        if org:
            org_id = org["id"]

    if org_id:
        org_id_int = int(org_id)

        # Link Stripe customer to org
        conn = sqlite3.connect(str(_get_db_path(settings.outputs_dir)))
        conn.execute(
            "UPDATE organizations SET stripe_customer_id = ? WHERE id = ?",
            (customer_id, org_id_int),
        )
        conn.commit()
        conn.close()

        # Update subscription tier
        _update_org_subscription(
            settings.outputs_dir, org_id_int, tier, "active", sub["id"]
        )

        # Promote members to max allowed role
        allowed_role = role_max_from_subscription(tier)
        _promote_org_members_to_max_role(settings.outputs_dir, org_id_int, allowed_role)


def _handle_subscription_updated(data: dict, settings: Settings) -> None:
    """Subscription updated (tier change, renewal)."""
    sub: dict = data["object"]
    customer_id: str = sub["customer"]
    status: str = sub["status"]
    price_id: str = sub["items"]["data"][0]["price"]["id"]
    tier: str = _price_id_to_tier(price_id, settings)

    org = _get_org_by_stripe_customer(settings.outputs_dir, customer_id)
    if org:
        mapped_status = (
            "active"
            if status == "active"
            else "past_due"
            if status == "past_due"
            else "canceled"
        )
        if mapped_status == "active":
            _update_org_subscription(
                settings.outputs_dir, org["id"], tier, mapped_status, sub["id"]
            )
            allowed_role = role_max_from_subscription(tier)
            _promote_org_members_to_max_role(
                settings.outputs_dir, org["id"], allowed_role
            )
        else:
            _update_org_subscription(
                settings.outputs_dir, org["id"], "free", mapped_status
            )


def _handle_subscription_deleted(data: dict, settings: Settings) -> None:
    """Subscription canceled or expired — revert org to free."""
    sub: dict = data["object"]
    customer_id: str = sub["customer"]
    org = _get_org_by_stripe_customer(settings.outputs_dir, customer_id)
    if org:
        _update_org_subscription(settings.outputs_dir, org["id"], "free", "canceled")


def _handle_invoice_payment_failed(data: dict, settings: Settings) -> None:
    """Payment failed — flag as past_due."""
    invoice: dict = data["object"]
    customer_id = invoice.get("customer")
    org = _get_org_by_stripe_customer(settings.outputs_dir, customer_id)
    if org:
        _update_org_subscription(settings.outputs_dir, org["id"], "free", "past_due")


_EVENT_HANDLERS: dict[str, Any] = {
    "customer.subscription.created": _handle_subscription_created,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.payment_succeeded": lambda d, s: None,
    "invoice.payment_failed": _handle_invoice_payment_failed,
}
