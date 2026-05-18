# 💰 Constellation Simulator — Pricing & Subscription Implementation

**Target:** Another LLM (Claude) implementing the freemium → Pro → Enterprise tier system.

**Goal:** Add Stripe billing, user tiers, rate limiting, job quotas, and feature gating to the Constellation Simulator web platform.

**⚠️ PREREQUISITE:** This document depends on the **RBAC & User Management** system defined in `documentation/rbac_user_management_implementation.md`. Implement that first.

---

### How Pricing Tiers Map to RBAC Roles

| Pricing Tier | RBAC Role | Sign-Up Method | Description |
|-------------|-----------|---------------|-------------|
| **Free** | `viewer` | No registration needed | **3 trial simulations** (heatmap only, PNG with watermark). Try before you buy. |
| **Demo** | `demo` | Register with `role=demo` | Full features, limited to 10 jobs or 14 days, then → `viewer` |
| **Pro** | `creator` | Subscribe via Stripe → webhook upgrades role | Full simulation access, 500 jobs/month, AI analysis |
| **Pro (team)** | `team_manager` | Org-level Pro subscription | Manages a team, invites creators/viewers |
| **Enterprise** | `team_manager` + extras | Enterprise subscription + admin override | Unlimited everything, API, SLA, on-premise |
| **Admin** | `admin` | Bootstrap from `.env` only | God mode — manages the entire SaaS |

**Key rule:** The `users.role` column (from RBAC) IS the source of truth for permissions. The `organizations.subscription_tier` column drives what roles can be assigned by the team manager. When a subscription changes, the webhook updates `org.subscription_tier`, and the team manager can then assign roles up to that tier's maximum.

```
org.subscription_tier  →  max_role_allowed
─────────────────────────────────────────
free / none            →  viewer only
pro                    →  creator (and optionally team_manager)
enterprise             →  team_manager (and unlimited creators/viewers)
```

### File Layout — Updated

This document only adds the **billing/pricing layer** on top of RBAC. Files marked `[RBAC]` come from the RBAC doc.

```
web/backend/app/
├── db.py                      ← [RBAC] Already has users, orgs, invitations tables
├── auth.py                    ← [RBAC] Already handles register/login with role+org
├── rbac.py                    ← [RBAC] Role hierarchy + permissions matrix
├── deps.py                    ← [RBAC] require_permission(), require_role_at_least()
│
├── tier_config.py             ← NEW (this doc): TIER_LIMITS + TIER_TO_ROLE_MAP
├── stripe_integration.py      ← NEW (this doc): Stripe webhooks, Checkout
├── rate_limiter.py            ← NEW (this doc): per-role rate limiting middleware
├── watermark.py               ← NEW (this doc): watermark overlay for free-tier
├── config.py                  ← MODIFY: add Stripe keys
├── main.py                    ← MODIFY: add startup + cleanup scheduler
├── api/
│   ├── billing_routes.py      ← NEW: /api/billing/* endpoints
│   ├── jobs_routes.py         ← [RBAC] Already scoped by user/org — add quota checks
│   └── options_routes.py      ← MODIFY: return tier-appropriate options filtered by role
└── worker/
    └── tasks.py               ← MODIFY: pass tier env var for watermark

web/frontend/src/
├── store/authStore.ts         ← [RBAC] Already has role, orgId, orgName
├── pages/
│   ├── DashboardPage.tsx      ← MODIFY: add upgrade CTA, tier badge
│   └── BillingPage.tsx        ← NEW: plans, upgrade, manage subscription
├── components/
│   ├── TierBadge.tsx          ← NEW: subscription tier indicator in header
│   └── UpgradeModal.tsx       ← NEW: modal when hitting limits
```

### Data Flow (Updated for RBAC integration)

```
User clicks "Upgrade to Pro"
  → Frontend calls POST /api/billing/create-checkout
  → Creates Stripe Checkout Session (org_id in metadata)
  → User redirected to Stripe

Stripe sends webhook: customer.subscription.updated
  → stripe_integration.py
  → Looks up org by stripe_customer_id (not user!)
  → Updates organizations.subscription_tier = "pro"
  → Optionally promotes org owner to "creator" (if currently "viewer"/"demo")

Next API request:
  → deps.get_current_user()        [RBAC — returns user with role]
  → tier_config.get_limits(role)    [maps role → tier limits]
  → Job quotas checked against role
  → Simulation runs with role-appropriate params
  → Exports get watermark if role == "viewer" (free tier)
  → 3 trial simulations completed → upgrade CTA shown
```

---

### 💰 Pricing Summary Table

| Tier | RBAC Role | Price | Monthly Jobs | Max Sats | AI Analyses | Export | Multi-Shell | TCO |
|------|-----------|-------|-------------|----------|-------------|--------|-------------|-----|
| **Free** | `viewer` | **€0** | **3** (trial) | 24 | ❌ | PNG | ❌ | ❌ |
| **Demo** | `demo` | **€0** (14 dias) | 10 | 250 | ✅ (3) | PNG, CSV, GIF, HTML | ✅ (3 shells) | ✅ |
| **Pro** | `creator` | **€299/mês** | 500 | 250 | ✅ (10) | PNG, CSV, GIF, HTML | ✅ (5 shells) | ✅ |
| **Pro (annual)** | `creator` | **€2.990/ano** (poupe ~17%) | 500 | 250 | ✅ (10) | PNG, CSV, GIF, HTML | ✅ (5 shells) | ✅ |
| **Enterprise** | `team_manager` | **€999/mês** | Ilimitado | Ilimitado | ✅ Ilimitado | Todos + JSON + API | ✅ Ilimitado | ✅ |
| **Enterprise (annual)** | `team_manager` | **€9.990/ano** (poupe ~17%) | Ilimitado | Ilimitado | ✅ Ilimitado | Todos + JSON + API | ✅ Ilimitado | ✅ |
| **Admin** | `admin` | Bootstrap only | Ilimitado | Ilimitado | ✅ Ilimitado | Todos | ✅ Ilimitado | ✅ |

**Notas:**
- **Free** inclui 3 simulações gratuitas sem registo (heatmap básico, marca d'água) — serve de amostra antes do registo
- Demo expira após 14 dias ou 10 simulações (o que acontecer primeiro) → rebaixado para `viewer`
- O funil de conversão: **Visitor → Free (3 trials) → Demo (10 jobs, 14d) → Pro (500 jobs/mês) → Enterprise (ilimitado)**
- Pro (team): inclui role `team_manager` para gerir equipa de creators/viewers
- Enterprise inclui suporte prioritário, SLA 99.9%, SSO/SAML, opção on-premise
- Todos os preços em Euros (€), IVA não incluído

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Database Schema](#2-database-schema)
3. [Tier Configuration](#3-tier-configuration)
4. [Stripe Integration (Backend)](#4-stripe-integration-backend)
5. [Rate Limiting & Middleware](#5-rate-limiting--middleware)
6. [Job Quotas & Validation](#6-job-quotas--validation)
7. [Feature Gating in Simulation](#7-feature-gating-in-simulation)
8. [Watermark on Free Tier](#8-watermark-on-free-tier)
9. [Auto-Cleanup of Expired Jobs](#9-auto-cleanup-of-expired-jobs)
10. [Frontend Components](#10-frontend-components)
11. [Validation](#11-validation)

---

## 1. Architecture Overview

### File Layout (new + modified)

```
web/backend/app/
├── main.py                    ← MODIFY: add startup event for DB init + cleanup scheduler
├── config.py                  ← MODIFY: add Stripe keys, DB path
├── db.py                      ← NEW: SQLite database models and helpers
├── stripe_integration.py      ← NEW: Stripe webhook handling + Checkout session creation
├── rate_limiter.py            ← NEW: per-user rate limiting middleware
├── tier_config.py             ← NEW: tier definitions + feature flag resolver
├── watermark.py               ← NEW: watermark overlay logic for free-tier exports
├── auth.py                    ← MODIFY: add tier info to JWT token payload
├── api/
│   ├── jobs_routes.py         ← MODIFY: check quotas before accepting jobs
│   ├── billing_routes.py      ← NEW: /api/billing/* endpoints
│   └── options_routes.py      ← MODIFY: return tier-appropriate options
└── worker/
    └── tasks.py               ← MODIFY: pass tier info to subprocess for watermark

web/frontend/src/
├── types.ts                   ← MODIFY: add Tier, BillingInfo types
├── api/client.ts              ← MODIFY: add billing API calls
├── store/authStore.ts         ← MODIFY: add tier field
├── pages/
│   ├── DashboardPage.tsx      ← MODIFY: add tier badge, upgrade CTA
│   └── BillingPage.tsx        ← NEW: plans, upgrade, manage subscription
├── components/
│   ├── TierBadge.tsx          ← NEW: tier indicator in header
│   ├── UpgradeModal.tsx       ← NEW: modal when hitting limits
│   └── FeatureBlocked.tsx     ← NEW: placeholder for locked features
└── web/backend/requirements.txt   ← MODIFY: add stripe, pyjwt[crypto]
```

### Data Flow

```
User clicks "Upgrade" → Stripe Checkout → Stripe sends webhook
                                           ↓
                              /api/billing/webhook (POST)
                                           ↓
                              Update SQLite: user.tier = "pro"
                                           ↓
                              Next API request: middleware reads tier
                                           ↓
                              Feature flags resolved from tier_config.py
                                           ↓
                              Job quotas checked in jobs_routes.py
                                           ↓
                              Simulation runs with tier-appropriate params
                                           ↓
                              Exports get watermark if free tier
```

---

## 2. Database Schema (Additions to RBAC Schema)

### File: `web/backend/app/db.py`

**DO NOT create a new `db.py`.** The RBAC document already defines `web/backend/app/db.py` with:

- `users` table (with `role`, `org_id`, `is_active`, `password_hash`, `email`, etc.)
- `organizations` table (with `owner_id`, `max_members`, etc.)
- `invitations` table
- `stripe_events` table (for webhook idempotency)
- All CRUD functions (`create_user`, `get_user_by_email`, etc.)

### Additions needed for billing

Extend the `organizations` table with billing fields:

```sql
-- Add these columns to the organizations table (ALTER TABLE, or include in RBAC's init_db)
ALTER TABLE organizations ADD COLUMN stripe_customer_id TEXT UNIQUE;
ALTER TABLE organizations ADD COLUMN stripe_subscription_id TEXT;
ALTER TABLE organizations ADD COLUMN subscription_tier TEXT DEFAULT 'free';
ALTER TABLE organizations ADD COLUMN subscription_status TEXT DEFAULT 'inactive';
ALTER TABLE organizations ADD COLUMN subscription_updated_at TEXT;
```

Also add this usage-tracking table for organizations:

```sql
CREATE TABLE IF NOT EXISTS org_usage (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id              INTEGER NOT NULL,
    month               TEXT    NOT NULL,   -- '2026-05'
    jobs_used           INTEGER DEFAULT 0,
    ai_analyses_used    INTEGER DEFAULT 0,
    storage_bytes       INTEGER DEFAULT 0,
    FOREIGN KEY (org_id) REFERENCES organizations(id),
    UNIQUE(org_id, month)
);
```

### Updated `tier_config.py` — The `TIER_TO_ROLE_MAP`

```python
"""
web/backend/app/tier_config.py — Tier definitions and feature flag resolution.

This file maps RBAC roles to feature limits. The pricing tier is stored on the
organization (organizations.subscription_tier), but the source of truth for
permissions is the user's `role` column (set by RBAC).

When a subscription updates, the Stripe webhook:
  1. Updates organizations.subscription_tier
  2. Promotes/demotes users within the org according to their new max allowed role
"""

from __future__ import annotations

# ── Map subscription tier → maximum RBAC role allowed ───────────────────────
# The team_manager can assign roles up to this level.
SUBSCRIPTION_MAX_ROLE = {
    "free":       "viewer",         # free orgs: read-only members
    "pro":        "creator",        # pro orgs: creators who can simulate
    "enterprise": "team_manager",   # enterprise: full team management
    # Note: "admin" role is NEVER assignable via subscription.
    #         It is bootstrap-only.
}

# ── Map RBAC role → feature limits ──────────────────────────────────────────
# These are the actual enforcement values. Role determines limits.
TIER_LIMITS = {
    "viewer": {                          # Free tier (3 trial simulations)
        "max_sats": 24,
        "max_planes": 6,
        "modes": ["heatmap"],
        "heatmap_resolution": 10.0,
        "jobs_per_month": 3,
        "concurrent_jobs": 1,
        "max_duration_min": 360,
        "export_formats": ["png"],
        "ai_analyses_per_month": 0,
        "retention_days": 90,
        "backends": ["matplotlib"],
        "multi_shell": False,
        "watermark": True,               # free outputs get watermarked
        "tco_analysis": False,
        "latency_mode": False,
        "max_shells": 1,
        "can_create_jobs": True,         # 3 trials allowed (no register needed)
        "max_jobs_total": 3,
    },
    "demo": {                            # Demo trial
        "max_sats": 250,
        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route"],
        "jobs_per_month": 10,
        "concurrent_jobs": 1,
        "heatmap_resolution": 2.0,
        "max_duration_min": 1440,
        "export_formats": ["png", "csv", "gif", "html"],
        "ai_analyses_per_month": 3,
        "retention_days": 14,
        "backends": ["matplotlib", "plotly"],
        "multi_shell": True,
        "watermark": False,              # no watermark during trial
        "tco_analysis": True,
        "latency_mode": False,
        "max_shells": 3,
        "can_create_jobs": True,
        "max_jobs_total": 10,            # hard limit for demo lifecycle
    },
    "creator": {                         # Pro tier
        "max_sats": 250,
        "max_planes": 72,
        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route"],
        "heatmap_resolution": 2.0,
        "jobs_per_month": 500,
        "concurrent_jobs": 3,
        "max_duration_min": 1440,
        "export_formats": ["png", "csv", "gif", "html"],
        "ai_analyses_per_month": 10,
        "retention_days": 90,
        "backends": ["matplotlib", "plotly"],
        "multi_shell": True,
        "watermark": False,
        "tco_analysis": True,
        "latency_mode": False,
        "max_shells": 5,
        "can_create_jobs": True,
        "max_jobs_total": -1,            # unlimited (within monthly quota)
    },
    "team_manager": {                    # Enterprise / Pro (team)
        "max_sats": 99999,
        "max_planes": 999,
        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route", "latency"],
        "heatmap_resolution": 0.5,
        "jobs_per_month": -1,
        "concurrent_jobs": 10,
        "max_duration_min": 10080,
        "export_formats": ["png", "csv", "gif", "html", "json"],
        "ai_analyses_per_month": -1,
        "retention_days": 365,
        "backends": ["matplotlib", "plotly", "bokeh"],
        "multi_shell": True,
        "watermark": False,
        "tco_analysis": True,
        "latency_mode": True,
        "max_shells": 999,
        "can_create_jobs": True,
        "max_jobs_total": -1,
    },
    "admin": {                           # God mode (all limits inherited from team_manager)
        "max_sats": 99999,
        "max_planes": 999,
        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route", "latency"],
        "heatmap_resolution": 0.5,
        "jobs_per_month": -1,
        "concurrent_jobs": 50,
        "ai_analyses_per_month": -1,
        "retention_days": 365,
        "backends": ["matplotlib", "plotly", "bokeh"],
        "multi_shell": True,
        "watermark": False,
        "tco_analysis": True,
        "latency_mode": True,
        "max_shells": 999,
        "can_create_jobs": True,
        "max_jobs_total": -1,
    },
}


def get_limits(role: str) -> dict:
    """Return the limits dict for a given RBAC role. Falls back to 'viewer'."""
    return TIER_LIMITS.get(role, TIER_LIMITS["viewer"])


def role_max_from_subscription(subscription_tier: str) -> str:
    """What's the max RBAC role this subscription tier allows?"""
    return SUBSCRIPTION_MAX_ROLE.get(subscription_tier, "viewer")


def validate_job_params(role: str, params: dict) -> list[str]:
    """Validate job parameters against role limits. Returns list of error messages."""
    limits = get_limits(role)
    errors = []

    if not limits.get("can_create_jobs", False):
        errors.append("Your role does not allow creating simulations. Upgrade to Pro.")
        return errors  # short-circuit, no point checking other params

    sats = params.get("sats", 0)
    if sats > limits["max_sats"]:
        errors.append(f"Max satellites: {limits['max_sats']} (requested: {sats})")

    # ... same pattern for planes, duration, shells, mode, etc.
    # (reuse from the original section 3 content below)

    return errors
```

---

## 3. Tier Configuration

### File: `web/backend/app/tier_config.py`

Single source of truth for all tier limits. Used by every component (middleware, jobs routes, frontend options).

```python
"""
web/backend/app/tier_config.py — Tier definitions and feature flag resolution.
"""

from __future__ import annotations
from typing import Optional

TIER_LIMITS = {
    "free": {
        "max_sats": 24,
        "max_planes": 6,
        "modes": ["heatmap", "sky", "track"],
        "heatmap_resolution": 10.0,        # minimum 10° grid
        "jobs_per_month": 10,
        "concurrent_jobs": 1,
        "max_duration_min": 360,           # 6 hours
        "export_formats": ["png"],
        "ai_analyses_per_month": 0,
        "retention_days": 7,
        "backends": ["matplotlib"],
        "multi_shell": False,
        "watermark": True,
        "tco_analysis": False,
        "latency_mode": False,
        "max_shells": 1,
    },
    "pro": {
        "max_sats": 250,
        "max_planes": 72,
        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route"],
        "heatmap_resolution": 2.0,
        "jobs_per_month": 500,
        "concurrent_jobs": 3,
        "max_duration_min": 1440,          # 24 hours
        "export_formats": ["png", "csv", "gif", "html"],
        "ai_analyses_per_month": 10,
        "retention_days": 90,
        "backends": ["matplotlib", "plotly"],
        "multi_shell": True,
        "watermark": False,
        "tco_analysis": True,
        "latency_mode": False,
        "max_shells": 5,
    },
    "enterprise": {
        "max_sats": 99999,
        "max_planes": 999,
        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route", "latency"],
        "heatmap_resolution": 0.5,
        "jobs_per_month": -1,              # -1 = unlimited
        "concurrent_jobs": 10,
        "max_duration_min": 10080,         # 7 days
        "export_formats": ["png", "csv", "gif", "html", "json"],
        "ai_analyses_per_month": -1,
        "retention_days": 365,
        "backends": ["matplotlib", "plotly", "bokeh"],
        "multi_shell": True,
        "watermark": False,
        "tco_analysis": True,
        "latency_mode": True,
        "max_shells": 999,
    },
}

STRIPE_PRICES = {
    "pro_monthly": {
        "id": "price_pro_monthly",   # Replace with actual Stripe Price ID
        "amount_cents": 29900,        # €299
        "currency": "eur",
        "interval": "month",
        "tier": "pro",
    },
    "pro_annual": {
        "id": "price_pro_annual",
        "amount_cents": 299000,       # €2,990 (2 months free)
        "currency": "eur",
        "interval": "year",
        "tier": "pro",
    },
    "enterprise_monthly": {
        "id": "price_enterprise_monthly",
        "amount_cents": 99900,
        "currency": "eur",
        "interval": "month",
        "tier": "enterprise",
    },
    "enterprise_annual": {
        "id": "price_enterprise_annual",
        "amount_cents": 999000,
        "currency": "eur",
        "interval": "year",
        "tier": "enterprise",
    },
}


def get_limits(tier: str) -> dict:
    """Return the limits dict for a given tier. Falls back to 'free'."""
    return TIER_LIMITS.get(tier, TIER_LIMITS["free"])


def mode_allowed(tier: str, mode: str) -> bool:
    """Check if a simulation mode is allowed for the user's tier."""
    limits = get_limits(tier)
    return mode in limits["modes"]


def job_quota_remaining(outputs_dir, username: str, tier: str) -> int:
    """Return remaining jobs this month. -1 = unlimited."""
    from .db import get_job_count
    limits = get_limits(tier)
    if limits["jobs_per_month"] == -1:
        return -1  # unlimited
    used = get_job_count(outputs_dir, username)
    return max(0, limits["jobs_per_month"] - used)


def validate_job_params(tier: str, params: dict) -> list[str]:
    """Validate job parameters against tier limits. Returns list of error messages."""
    limits = get_limits(tier)
    errors = []

    # Satellite count
    sats = params.get("sats", 0)
    if sats > limits["max_sats"]:
        errors.append(f"Max satellites for {tier} tier is {limits['max_sats']} (requested: {sats})")

    # Planes
    planes = params.get("planes", 0)
    if planes > limits["max_planes"]:
        errors.append(f"Max planes for {tier} tier is {limits['max_planes']} (requested: {planes})")

    # Duration
    duration = params.get("duration", 0)
    if duration > limits["max_duration_min"]:
        errors.append(f"Max duration for {tier} tier is {limits['max_duration_min']} min")

    # Multi-shell
    shells = params.get("shells", None)
    if shells and not limits["multi_shell"]:
        errors.append("Multi-shell is not available on the Free tier")
    if shells and isinstance(shells, list) and len(shells) > limits["max_shells"]:
        errors.append(f"Max {limits['max_shells']} shells allowed on {tier} tier")

    # Mode
    mode = params.get("mode", "")
    if not mode_allowed(tier, mode):
        errors.append(f"Mode '{mode}' is not available on the {tier} tier")

    return errors
```

---

## 4. Stripe Integration (Backend) — Org-Level Billing

**IMPORTANT:** Billing is at the **organization** level, not the user level. A Pro subscription upgrades the entire org. The webhook updates `organizations.subscription_tier`, and then users within the org can have roles up to the tier's maximum (defined in `tier_config.SUBSCRIPTION_MAX_ROLE`).

### File: `web/backend/app/stripe_integration.py`

```python
"""
web/backend/app/stripe_integration.py — Stripe Checkout + Webhook handling.

Billing is org-level. The Stripe Customer object is attached to the organization,
not the individual user. When a subscription changes, the webhook:
  1. Updates organizations.subscription_tier
  2. Promotes the org owner to the max role allowed by the new tier
  3. Leaves other members at their current role (they keep what they had)

Environment variables (in .env):
  STRIPE_SECRET_KEY:     sk_live_... or sk_test_...
  STRIPE_WEBHOOK_SECRET: whsec_... (for signature verification)
  STRIPE_PRICE_PRO:      price_xxx (monthly)
  STRIPE_PRICE_PRO_YEAR: price_xxx (annual)
  STRIPE_PRICE_ENT:      price_xxx (enterprise monthly)
  STRIPE_PRICE_ENT_YEAR: price_xxx (enterprise annual)
  APP_URL:               https://constellation-sim.example.com
"""

from __future__ import annotations

import json
import stripe
from stripe import StripeError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
import sqlite3

from .config import Settings, get_settings
from .auth import get_current_user
from .deps import require_permission
from .rbac import role_is_at_least
from .db import (
    get_user_by_email,
    _get_db_path,
    mark_stripe_event,
    get_organization,
)
from .tier_config import role_max_from_subscription, get_limits

router = APIRouter(prefix="/api/billing", tags=["billing"])


def setup_stripe(settings: Settings):
    stripe.api_key = settings.stripe_secret_key


# ── Helper: get org by stripe customer ID ─────────────────────────────────────

def _get_org_by_stripe_customer(outputs_dir, customer_id):
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM organizations WHERE stripe_customer_id = ?",
        (customer_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def _update_org_subscription(outputs_dir, org_id, tier, status, sub_id=None):
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """UPDATE organizations
           SET subscription_tier = ?, subscription_status = ?,
               subscription_updated_at = ?,
               stripe_subscription_id = COALESCE(?, stripe_subscription_id)
           WHERE id = ?""",
        (tier, status, now, sub_id, org_id),
    )
    conn.commit()
    conn.close()


def _promote_org_members_to_max_role(outputs_dir, org_id, allowed_role):
    """Promote members up to the max role their subscription allows.
    Never demotes anyone — if a member is already team_manager, they stay."""
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.row_factory = sqlite3.Row
    members = conn.execute(
        "SELECT id, role FROM users WHERE org_id = ?", (org_id,),
    ).fetchall()
    for m in members:
        current = m["role"]
        # Only upgrade if the new allowed role is higher than current
        # (never downgrade existing members)
        rank = {"viewer": 0, "demo": 1, "creator": 2, "team_manager": 3, "admin": 4}
        if rank.get(allowed_role, 0) > rank.get(current, 0):
            conn.execute(
                "UPDATE users SET role = ? WHERE id = ?",
                (allowed_role, m["id"]),
            )
    conn.commit()
    conn.close()


# ── Checkout Session ─────────────────────────────────────────────────────────

@router.post("/create-checkout")
async def create_checkout(
    price_id: str,
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("billing:manage")),
    settings: Settings = Depends(get_settings),
):
    """
    Create a Stripe Checkout Session for the user's organization.

    The checkout is linked to the org via metadata.org_id.
    After payment, the webhook looks up the org by stripe_customer_id.
    """
    setup_stripe(settings)

    org = get_organization(settings.outputs_dir, user["org_id"])
    if not org:
        raise HTTPException(status_code=400, detail="No organization found")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=user["email"],
            client_reference_id=str(org["id"]),
            success_url=f"{settings.app_url}/billing?success=true",
            cancel_url=f"{settings.app_url}/billing?canceled=true",
            metadata={"org_id": str(org["id"]), "org_name": org["name"]},
            allow_promotion_codes=True,
            tax_id_collection={"enabled": True},
        )
        return {"url": session.url}
    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Customer Portal (manage subscription) ────────────────────────────────────

@router.get("/portal")
async def billing_portal(
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("billing:manage")),
    settings: Settings = Depends(get_settings),
):
    """Return a Stripe Customer Portal URL for managing the org subscription."""
    setup_stripe(settings)
    org = get_organization(settings.outputs_dir, user["org_id"])
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


# ── Current subscription info ────────────────────────────────────────────────

@router.get("/subscription")
async def get_subscription(
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Return current subscription info for the user's organization."""
    org = get_organization(settings.outputs_dir, user["org_id"])
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    limits = get_limits(user["role"])

    return {
        "tier": org.get("subscription_tier", "free"),
        "subscription_status": org.get("subscription_status", "inactive"),
        "org_id": org["id"],
        "org_name": org["name"],
        "role": user["role"],
        "jobs_remaining": -1 if limits.get("jobs_per_month", 0) == -1
                          else max(0, limits["jobs_per_month"] - user.get("jobs_used_this_month", 0)),
        "jobs_used": user.get("jobs_used_this_month", 0),
        "jobs_limit": limits.get("jobs_per_month", 0),
        "demo_jobs_remaining": max(0, user.get("demo_jobs_limit", 0) - user.get("demo_jobs_used", 0))
                               if user["role"] == "demo" else None,
    }


# ── Webhook ──────────────────────────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
):
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

    # Idempotency check
    if not mark_stripe_event(settings.outputs_dir, event.id, event.type, json.dumps(event.data)):
        return JSONResponse(content={"status": "duplicate"}, status_code=200)

    handler = _EVENT_HANDLERS.get(event.type)
    if handler:
        await handler(event.data, settings)

    return JSONResponse(content={"status": "ok"}, status_code=200)


# ── Event Handlers ───────────────────────────────────────────────────────────

async def _handle_subscription_created(data: dict, settings: Settings):
    """New subscription: link org to Stripe customer, upgrade tier."""
    sub = data["object"]
    customer_id = sub["customer"]
    price_id = sub["items"]["data"][0]["price"]["id"]
    tier = _price_id_to_tier(price_id, settings)

    # Find org by metadata (set during checkout)
    metadata = sub.get("metadata", {})
    org_id = metadata.get("org_id")

    if not org_id:
        # Fallback: find org by existing stripe_customer_id
        org = _get_org_by_stripe_customer(settings.outputs_dir, customer_id)
        if org:
            org_id = org["id"]

    if org_id:
        org_id = int(org_id)

        # Link Stripe customer to org
        conn = sqlite3.connect(str(_get_db_path(settings.outputs_dir)))
        conn.execute(
            "UPDATE organizations SET stripe_customer_id = ? WHERE id = ?",
            (customer_id, org_id),
        )
        conn.commit()
        conn.close()

        # Update subscription
        _update_org_subscription(settings.outputs_dir, org_id, tier, "active", sub["id"])

        # Promote owner + members to the max allowed role
        allowed_role = role_max_from_subscription(tier)
        _promote_org_members_to_max_role(settings.outputs_dir, org_id, allowed_role)


async def _handle_subscription_updated(data: dict, settings: Settings):
    """Subscription updated (tier change, renewal)."""
    sub = data["object"]
    customer_id = sub["customer"]
    status = sub["status"]
    price_id = sub["items"]["data"][0]["price"]["id"]
    tier = _price_id_to_tier(price_id, settings)

    org = _get_org_by_stripe_customer(settings.outputs_dir, customer_id)
    if org:
        mapped_status = (
            "active" if status == "active"
            else "past_due" if status == "past_due"
            else "canceled"
        )
        if mapped_status == "active":
            _update_org_subscription(settings.outputs_dir, org["id"], tier, mapped_status, sub["id"])
            allowed_role = role_max_from_subscription(tier)
            _promote_org_members_to_max_role(settings.outputs_dir, org["id"], allowed_role)
        else:
            _update_org_subscription(settings.outputs_dir, org["id"], "free", mapped_status)


async def _handle_subscription_deleted(data: dict, settings: Settings):
    """Subscription canceled or expired — revert org to free."""
    sub = data["object"]
    customer_id = sub["customer"]
    org = _get_org_by_stripe_customer(settings.outputs_dir, customer_id)
    if org:
        _update_org_subscription(settings.outputs_dir, org["id"], "free", "canceled")


async def _handle_invoice_payment_failed(data: dict, settings: Settings):
    """Payment failed — flag as past_due."""
    invoice = data["object"]
    customer_id = invoice.get("customer")
    org = _get_org_by_stripe_customer(settings.outputs_dir, customer_id)
    if org:
        _update_org_subscription(settings.outputs_dir, org["id"], "free", "past_due")


_EVENT_HANDLERS = {
    "customer.subscription.created": _handle_subscription_created,
    "customer.subscription.updated": _handle_subscription_updated,
    "customer.subscription.deleted": _handle_subscription_deleted,
    "invoice.payment_succeeded": lambda d, s: None,
    "invoice.payment_failed": _handle_invoice_payment_failed,
}


def _price_id_to_tier(price_id: str, settings: Settings) -> str:
    mapping = {
        settings.stripe_price_pro: "pro",
        settings.stripe_price_pro_year: "pro",
        settings.stripe_price_ent: "enterprise",
        settings.stripe_price_ent_year: "enterprise",
    }
    return mapping.get(price_id, "free")
```

### Config additions

In `web/backend/app/config.py`, add:

```python
class Settings(BaseSettings):
    # ... existing fields (from RBAC doc) ...

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_pro_year: str = ""
    stripe_price_ent: str = ""
    stripe_price_ent_year: str = ""
    app_url: str = "http://localhost"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### Routes registration

In `web/backend/app/main.py`:

```python
from .stripe_integration import router as billing_router
app.include_router(billing_router)
```

---

## 5. Rate Limiting & Middleware

### File: `web/backend/app/rate_limiter.py`

```python
"""
web/backend/app/rate_limiter.py — Per-user rate limiting middleware.

Uses a simple in-memory sliding window counter per user_id (extracted from JWT).
For production (multi-worker), use Redis. For single-worker (this project),
an in-memory dict is sufficient.

**RBAC Integration:** The rate limit is determined by the user's **RBAC role**,
not their subscription tier. The `decode_token_from_request()` function
(defined in RBAC's `auth.py`) extracts the email from the JWT, then we look up
the user's role from the DB.

Apply as FastAPI middleware.
"""

import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from .auth import decode_token_from_request

# Rate limits per RBAC role (requests per minute)
RATE_LIMITS = {
    "viewer":        10,
    "demo":          20,
    "creator":       60,
    "team_manager":  120,
    "admin":         600,
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter per user + role.

    Tracks timestamps of recent requests per user email.
    If user exceeds their role's rate limit, returns 429.
    """

    def __init__(self, app):
        super().__init__(app)
        self._windows: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for webhook and public endpoints
        path = request.url.path
        if path.startswith("/api/billing/webhook") or path.startswith("/api/reports/shared"):
            return await call_next(request)

        # Extract user email from JWT
        user_email = decode_token_from_request(request)
        if user_email is None:
            return await call_next(request)

        # Determine role from DB
        from .db import get_user_by_email
        from .config import get_settings

        settings = get_settings()
        db_user = get_user_by_email(settings.outputs_dir, user_email)
        role = db_user["role"] if db_user else "viewer"
        limit = RATE_LIMITS.get(role, 10)

        # Slide window
        now = time.time()
        window = self._windows[user_email]

        # Remove timestamps older than 60 seconds
        while window and window[0] < now - 60:
            window.popleft()

        if len(window) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded ({limit} requests/minute for {role} role).",
                    "role": role,
                    "limit": limit,
                    "retry_after_seconds": int(60 - (now - window[0])),
                },
            )

        window.append(now)
        return await call_next(request)
```

### Apply middleware

In `web/backend/app/main.py`:

```python
from .rate_limiter import RateLimitMiddleware

app.add_middleware(RateLimitMiddleware)
```

**Note:** The `decode_token_from_request` function is already defined in the RBAC document's `auth.py`. No need to redefine it here — just import it.

---

## 6. Job Quotas & Validation

### Modify: `web/backend/app/api/jobs_routes.py`

In the `submit_job` endpoint, add validation before queueing:

```python
from ..tier_config import validate_job_params, get_limits, role_max_from_subscription
from ..rbac import has_permission, get_effective_role
from ..db import get_user_by_email, increment_job_count


@router.post("/jobs")
async def submit_job(
    body: JobRequest,
    user: dict = Depends(get_current_user),   # ← RBAC returns a dict, not a string
    settings: Settings = Depends(get_settings),
):
    # get_effective_role handles demo expiry automatically
    role = get_effective_role(user)

    # ── 1. Check permission ──────────────────────────────────────────
    if not has_permission(role, "jobs:create"):
        raise HTTPException(
            status_code=403,
            detail=f"Role '{role}' does not allow creating simulations.",
        )

    # ── 2. Check demo limit ─────────────────────────────────────────
    if role == "demo":
        demo_used = user.get("demo_jobs_used", 0)
        demo_limit = user.get("demo_jobs_limit", 10)
        if demo_used >= demo_limit:
            raise HTTPException(
                status_code=429,
                detail="Demo simulation limit reached. Upgrade to Pro.",
            )

    # ── 3. Check monthly job quota ──────────────────────────────────
    limits = get_limits(role)
    monthly_limit = limits["jobs_per_month"]
    jobs_used = user.get("jobs_used_this_month", 0)
    if monthly_limit != -1 and jobs_used >= monthly_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly job limit reached ({monthly_limit}/{monthly_limit}). Upgrade or wait.",
        )

    # ── 4. Validate params against role limits ──────────────────────
    errors = validate_job_params(role, body.params.model_dump())
    if errors:
        raise HTTPException(status_code=403, detail="; ".join(errors))

    # ── 5. Check concurrent job limit ───────────────────────────────
    active_jobs = sum(
        1 for j in list_jobs(settings.outputs_dir)
        if j.get("status") in ("queued", "running")
        and (j.get("org_id") == user.get("org_id") or role == "admin")
    )
    if active_jobs >= limits["concurrent_jobs"]:
        raise HTTPException(status_code=429, detail="Concurrent job limit reached.")

    # ── 6. Increment counter and submit job ─────────────────────────
    # Use email-based increment to align with RBAC's DB schema
    increment_job_count(settings.outputs_dir, user["email"])

    # Set ownership metadata for this job
    job_meta = {
        "user_id": user["id"],
        "org_id": user.get("org_id"),
        "user_email": user["email"],
        "username": user.get("username", user["email"]),
        "role": role,
        # ... rest of job params
    }

    # ... existing job creation / queueing logic ...
```

### Options route: filter by role (not tier)

In `web/backend/app/api/options_routes.py`, modify the `get_options` endpoint to filter available modes/backends by the requesting user's RBAC role. The `get_current_user` dependency from RBAC already returns a dict with `role`.

```python
from ..rbac import get_effective_role
from ..tier_config import get_limits
from ..db import get_user_by_email

@router.get("")
async def get_options(
    app_settings=Depends(get_settings),
    user: dict = Depends(get_current_user),  # ← RBAC dict
):
    c = _get_sim_constants()
    role = get_effective_role(user)          # ← handles demo expiry
    limits = get_limits(role)

    # Filter modes, backends based on role
    available_modes = limits["modes"]
    available_backends = limits["backends"]

    return {
        # ... existing fields ...
        "modes": available_modes,
        "backends": available_backends,
        "role": role,
        "limits": {
            "max_sats": limits["max_sats"],
            "jobs_per_month": limits["jobs_per_month"],
            "concurrent_jobs": limits["concurrent_jobs"],
            "heatmap_resolution": limits["heatmap_resolution"],
            "multi_shell": limits["multi_shell"],
            "export_formats": limits["export_formats"],
        },
    }
```

---

## 7. Feature Gating in Simulation

The `satsim_radio.py` CLI runs as a **subprocess** from the RQ worker. It doesn't know about user tiers. Instead:

1. **The web backend validates** before queueing (step 6 above)
2. **The worker passes tier info** as an environment variable to the subprocess
3. **The plot modules check** a `CONSTELLATION_SIM_TIER` env var to decide whether to watermark

### Modify worker: `web/backend/worker/tasks.py`

When constructing the subprocess call for a job, pass the user's tier:

```python
# In the task function that runs satsim_radio.py:
env = os.environ.copy()
env["CONSTELLATION_SIM_TIER"] = job_data.get("tier", "free")

subprocess.run(
    [venv_python, "satsim_radio.py", mode, *args],
    env=env,
    cwd=output_dir,
    capture_output=True,
    timeout=600,
)
```

The job metadata (`job_data`) should include the `tier` field, set when the job was submitted from `jobs_routes.py`.

---

## 8. Watermark on Free Tier

### File: `web/backend/app/watermark.py`

```python
"""
web/backend/app/watermark.py — Add watermark overlay to free-tier images.

The watermark is applied AFTER the simulator generates the image,
by post-processing the PNG output file.

Approach: Use Pillow to overlay semi-transparent text.
"""

import os
from PIL import Image, ImageDraw, ImageFont

WATERMARK_TEXT = "Constellation Simulator · Free Tier"
WATERMARK_OPACITY = 80  # 0-255 (lower = more transparent)


def should_watermark(tier: str) -> bool:
    """Only watermark free tier outputs."""
    return tier == "free"


def apply_watermark(filepath: str):
    """Apply a diagonal watermark to the given image file.

    Works on PNG images. Skips non-image files (CSV, GIF, HTML, etc.).
    """
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg"):
        return  # skip non-image files

    try:
        img = Image.open(filepath).convert("RGBA")
    except Exception:
        return

    # Create a transparent overlay
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Try to load a font; fall back to default
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # Draw watermark diagonally across the image
    text = WATERMARK_TEXT
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Multiple repeats across the image for full coverage
    step_x = text_w + 100
    step_y = text_h + 100

    for y in range(-text_h, img.height + text_h, step_y):
        for x in range(-text_w, img.width + text_w, step_x):
            draw.text(
                (x, y),
                text,
                font=font,
                fill=(128, 128, 128, WATERMARK_OPACITY),
            )

    # Composite and save
    watermarked = Image.alpha_composite(img, overlay)
    watermarked.convert("RGB").save(filepath, "PNG")
```

### Hook into worker output processing

In `web/backend/worker/tasks.py` (or in a post-job hook in `job_store.py`), after the simulator completes:

```python
# After subprocess.run, in the worker task:
if env.get("CONSTELLATION_SIM_TIER") == "free":
    from ..app.watermark import apply_watermark

    output_dir_path = Path(output_dir)
    for f in output_dir_path.glob("*.png"):
        apply_watermark(str(f))
```

---

## 9. Auto-Cleanup of Expired Jobs

### Add to scheduler in `web/backend/app/main.py`

Use APScheduler or a simple RQ scheduled job (whichever is simpler — RQ scheduler is already available).

```python
# In web/backend/app/main.py or a new file web/backend/app/cleanup.py

"""
web/backend/app/cleanup.py — Scheduled job cleanup based on tier retention.
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path


def cleanup_expired_jobs(outputs_dir: Path):
    """Remove job directories older than their tier's retention period.

    Each job directory at {outputs_dir}/{job_id}/ has a job.json with:
      - created_at: ISO datetime
      - tier: str

    Retention periods:
      free:       7 days
      pro:        90 days
      enterprise: 365 days

    This function is called by the RQ scheduler every 24 hours.
    """
    from .db import get_user_by_username
    from .tier_config import get_limits

    now = datetime.now(timezone.utc)

    for job_dir in outputs_dir.iterdir():
        if not job_dir.is_dir():
            continue

        job_meta_path = job_dir / "job.json"
        if not job_meta_path.exists():
            continue

        try:
            import json
            meta = json.loads(job_meta_path.read_text())
        except (json.JSONDecodeError, IOError):
            continue

        created_at_str = meta.get("created_at")
        tier = meta.get("tier", "free")

        if not created_at_str:
            continue

        try:
            created_at = datetime.fromisoformat(created_at_str)
        except (ValueError, TypeError):
            continue

        retention_days = get_limits(tier)["retention_days"]
        age_days = (now - created_at).days

        if age_days > retention_days:
            shutil.rmtree(str(job_dir))
```

To schedule this, add an RQ job in the `startup` event:

```python
# In web/backend/app/main.py:
from redis import Redis
from rq import Queue
from .cleanup import cleanup_expired_jobs

@app.on_event("startup")
async def startup():
    # ... existing startup code ...

    # Schedule daily cleanup
    redis_conn = Redis.from_url(settings.redis_url)
    scheduler_queue = Queue("default", connection=redis_conn)
    # Run every 24 hours
    scheduler_queue.enqueue_in(
        timedelta(hours=24),
        cleanup_expired_jobs,
        settings.outputs_dir,
    )
```

**Note:** For simplicity, you can also run this as a cron job on the host machine via the `cronjob` tool:

```
python3 -c "from app.cleanup import cleanup_expired_jobs; from pathlib import Path; cleanup_expired_jobs(Path('/app/outputs'))"
```

---

## 10. Frontend Components

**Integration with RBAC:** The RBAC document defines `RoleBadge.tsx` (shows `admin`/`team_manager`/`creator`/`viewer`/`demo`).
This pricing document adds `TierBadge.tsx` (shows the org's subscription: `Free`/`Pro`/`Enterprise`).
Both badges can coexist in the header — RoleBadge on the left (who you are), TierBadge on the right (what you pay for).

The `authStore.tsx` (from RBAC) already exposes:
- `role` — the user's RBAC role
- `orgId`, `orgName` — the org
- `tier` derived from the `/api/billing/subscription` endpoint response (stored as `subscriptionTier`)

### 10a. `RoleBadge.tsx` (from RBAC doc)

Already defined in `documentation/rbac_user_management_implementation.md`. Shows role with colour-coded badges.

### 10b. `TierBadge.tsx` (new — this doc)

Shows the organization's active subscription tier instead of the individual user's role.

```tsx
// web/frontend/src/components/TierBadge.tsx

interface TierBadgeProps {
  tier: 'free' | 'pro' | 'enterprise'
  className?: string
}

const COLORS = {
  free:       'bg-gray-700 text-gray-300',
  pro:        'bg-indigo-600 text-white',
  enterprise: 'bg-amber-600 text-white',
}

const LABELS = {
  free:       'Free',
  pro:        'Pro',
  enterprise: 'Enterprise',
}

export default function TierBadge({ tier, className = '' }: TierBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${COLORS[tier]} ${className}`}
    >
      {tier === 'pro' && <span className="w-1.5 h-1.5 rounded-full bg-indigo-300 animate-pulse" />}
      {tier === 'enterprise' && <span className="w-1.5 h-1.5 rounded-full bg-amber-300 animate-pulse" />}
      {LABELS[tier]}
    </span>
  )
}
```

### 10b. `UpgradeModal.tsx`

```tsx
// web/frontend/src/components/UpgradeModal.tsx
import { X, TrendingUp, Satellite, Brain, Download } from 'lucide-react'

interface UpgradeModalProps {
  open: boolean
  onClose: () => void
  reason?: string       // e.g. "Monthly job limit reached"
  suggestedTier?: string // "pro" or "enterprise"
}

const FEATURES = {
  pro: [
    { icon: Satellite, text: 'Up to 250 satellites, 72 planes' },
    { icon: TrendingUp, text: '500 simulations/month, 3 concurrent jobs' },
    { icon: Brain, text: 'AI-powered analysis (10/month)' },
    { icon: Download, text: 'Export: PNG, CSV, GIF, HTML (Plotly)' },
    { text: 'Multi-shell constellations (up to 5 shells)' },
    { text: 'Full TCO analysis' },
    { text: '90-day job retention' },
  ],
}

export default function UpgradeModal({ open, onClose, reason, suggestedTier = 'pro' }: UpgradeModalProps) {
  if (!open) return null

  const price = suggestedTier === 'enterprise' ? '€999' : '€299'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gray-900 rounded-2xl border border-gray-700 shadow-2xl max-w-lg w-full mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold text-white">Upgrade to {suggestedTier === 'enterprise' ? 'Enterprise' : 'Pro'}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Reason */}
        {reason && (
          <div className="px-6 py-3 bg-gray-800/50 border-b border-gray-800">
            <p className="text-sm text-amber-400">{reason}</p>
          </div>
        )}

        {/* Features */}
        <div className="px-6 py-4 space-y-3">
          {FEATURES.pro.map((feat, i) => (
            <div key={i} className="flex items-center gap-3 text-sm text-gray-300">
              {feat.icon ? <feat.icon className="w-4 h-4 text-indigo-400 shrink-0" /> : <div className="w-4 h-4" />}
              <span>{feat.text}</span>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="px-6 py-4 border-t border-gray-800 bg-gray-900/50">
          <p className="text-center text-2xl font-bold text-white mb-1">
            {price}<span className="text-sm font-normal text-gray-400">/month</span>
          </p>
          <p className="text-center text-xs text-gray-500 mb-4">
            Or €{suggestedTier === 'enterprise' ? '9,990' : '2,990'}/year (save ~17%)
          </p>
          <button className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-colors">
            Upgrade Now
          </button>
          <p className="text-center text-xs text-gray-600 mt-2">Cancel anytime. No questions asked.</p>
        </div>
      </div>
    </div>
  )
}
```

### 10c. `BillingPage.tsx` — Pricing Page (3-Column Layout)

New page at `/billing` with transparent pricing display:

```tsx
// web/frontend/src/pages/BillingPage.tsx
// Pricing page: 3 vertical columns showing tier name, price, features clearly

import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'
import { getSubscription, createCheckoutSession } from '../api/client'
import TierBadge from '../components/TierBadge'
import RoleBadge from '../components/RoleBadge'
import {
  Check, X as XIcon, Zap, Building2, Satellite, Brain,
  Download, TrendingUp, Globe, Shield, Cpu, Infinity,
} from 'lucide-react'

// ── Plan definitions ─────────────────────────────────────────────────────────

interface PlanFeature {
  text: string
  included: boolean
  icon?: any
  highlight?: boolean
}

interface Plan {
  id: string
  name: string
  tagline: string
  price: string
  period: string
  annualPrice?: string
  annualPeriod?: string
  description: string
  color: string
  borderColor: string
  bgColor: string
  icon: any
  features: PlanFeature[]
  cta: string
  priceId?: string
  popular?: boolean
  disabled?: boolean
}

const PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    tagline: 'Explore the platform',
    price: '€0',
    period: 'forever',
    description: 'Perfect for students and hobbyists to explore satellite constellation design.',
    color: 'text-gray-400',
    borderColor: 'border-gray-800',
    bgColor: 'bg-gray-900/50',
    icon: null,
    features: [
      { text: '3 free simulations to try the platform', included: true, icon: TrendingUp, highlight: true },
      { text: 'Heatmap mode (10° resolution)', included: true, icon: Globe },
      { text: 'PNG export with watermark', included: true, icon: Download },
      { text: 'View shared reports & simulations', included: true },
      { text: 'Multi-shell constellations', included: false, icon: XIcon },
      { text: 'TCO analysis', included: false, icon: XIcon },
      { text: 'AI-powered analysis', included: false, icon: XIcon },
      { text: 'Plotly interactive export', included: false, icon: XIcon },
      { text: 'Team management', included: false, icon: XIcon },
    ],
    cta: 'Current Plan',
    disabled: true,
  },
  {
    id: 'pro',
    name: 'Pro',
    tagline: 'For serious constellation designers',
    price: '€299',
    period: '/month',
    annualPrice: '€2.990',
    annualPeriod: '/year',
    description: 'Everything you need to design, simulate, and analyse satellite constellations professionally.',
    color: 'text-indigo-400',
    borderColor: 'border-indigo-500',
    bgColor: 'bg-indigo-900/10',
    icon: Zap,
    features: [
      { text: 'Up to 250 satellites, 72 orbital planes', included: true, icon: Satellite, highlight: true },
      { text: '500 simulations per month', included: true, icon: TrendingUp },
      { text: '3 concurrent simulation jobs', included: true },
      { text: 'Multi-shell (up to 5 shells)', included: true, icon: Globe },
      { text: 'Full RF link budget analysis', included: true },
      { text: 'Complete TCO business model', included: true, icon: TrendingUp },
      { text: 'AI analysis (10 per month)', included: true, icon: Brain },
      { text: 'Export: PNG, CSV, GIF, HTML (Plotly)', included: true, icon: Download },
      { text: '90-day job retention', included: true },
      { text: '5x higher API rate limit', included: true },
      { text: '3 team members included', included: true },
    ],
    cta: 'Subscribe',
    priceId: 'price_pro_monthly',
    popular: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    tagline: 'For teams & mission-critical ops',
    price: '€999',
    period: '/month',
    annualPrice: '€9.990',
    annualPeriod: '/year',
    description: 'Unlimited simulations, API access, dedicated support, and on-premise deployment options.',
    color: 'text-amber-400',
    borderColor: 'border-amber-600',
    bgColor: 'bg-amber-900/10',
    icon: Building2,
    features: [
      { text: 'Unlimited satellites & planes', included: true, icon: Infinity, highlight: true },
      { text: 'Unlimited simulations per month', included: true, icon: Infinity },
      { text: '10 concurrent simulation jobs', included: true },
      { text: 'Multi-shell (unlimited shells)', included: true },
      { text: 'End-to-end latency / ISL routing', included: true, icon: Globe },
      { text: 'Unlimited AI analysis', included: true, icon: Brain },
      { text: 'JSON API + webhooks', included: true, icon: Cpu },
      { text: 'Priority support + 99.9% SLA', included: true, icon: Shield },
      { text: 'SSO / SAML authentication', included: true, icon: Shield },
      { text: 'On-premise deployment option', included: true },
      { text: 'White-label option', included: true },
      { text: 'Unlimited team members', included: true },
      { text: 'Custom AI model configuration', included: true },
      { text: '365-day job retention', included: true },
    ],
    cta: 'Subscribe',
    priceId: 'price_enterprise_monthly',
  },
]


// ── Component ────────────────────────────────────────────────────────────────

export default function BillingPage() {
  const { tier, role, orgName } = useAuthStore()
  const [subscription, setSubscription] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [annual, setAnnual] = useState(false)

  const [promoCode, setPromoCode] = useState('')
  const [promoStatus, setPromoStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [promoMessage, setPromoMessage] = useState('')

  useEffect(() => {
    getSubscription()
      .then(setSubscription)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSubscribe = async (priceId: string, planId: string) => {
    if (planId === 'enterprise') {
      // Enterprise: redirect to contact form or checkout
      const result = await createCheckoutSession(priceId)
      if (result?.url) window.location.href = result.url
      return
    }
    const result = await createCheckoutSession(priceId)
    if (result?.url) window.location.href = result.url
  }

  const handleRedeem = async () => {
    if (!promoCode.trim()) return
    setPromoStatus('loading')
    try {
      const axios = (await import('axios')).default
      const result = await axios.post('/api/billing/redeem', { code: promoCode.trim() })
      setPromoStatus('success')
      setPromoMessage(result.data.message)
      setPromoCode('')
    } catch (err: any) {
      setPromoStatus('error')
      setPromoMessage(err.response?.data?.detail || 'Invalid code')
    }
  }

  // Plan matching
  const currentPlan = PLANS.find(p => p.id === tier) || PLANS[0]

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="border-b border-gray-800 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Billing & Plan</h1>
              <p className="text-gray-400 mt-1">
                {orgName || 'Personal'} · <RoleBadge role={role} /> · <TierBadge tier={tier} />
              </p>
            </div>
            {subscription?.subscription_status === 'active' && (
              <button
                onClick={async () => {
                  const axios = (await import('axios')).default
                  const res = await axios.get('/api/billing/portal')
                  if (res.data?.url) window.location.href = res.data.url
                }}
                className="px-4 py-2 rounded-lg border border-gray-700 text-sm text-gray-300
                           hover:bg-gray-800 hover:text-white transition-colors"
              >
                Manage Subscription
              </button>
            )}
          </div>

          {/* Usage bar */}
          {subscription && (
            <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
              {role === 'viewer' && !subscription.demo_jobs_remaining ? (
                <span className="text-indigo-400">
                  Free tier: 3 trial simulations available
                </span>
              ) : subscription.jobs_remaining !== undefined && subscription.jobs_remaining >= 0 ? (
                <span>
                  Simulations this month:{' '}
                  <span className="text-gray-300 font-semibold">{subscription.jobs_used || 0}</span>
                  /<span className="text-gray-400">{subscription.jobs_limit || '∞'}</span>
                  <span className="text-gray-600 ml-2">
                    ({subscription.jobs_remaining} remaining)
                  </span>
                </span>
              ) : subscription.role === 'demo' && subscription.demo_jobs_remaining !== undefined ? (
                <span className="text-amber-400">
                  Demo: {subscription.demo_jobs_remaining} simulations remaining
                </span>
              ) : (
                <span className="text-green-400">Unlimited simulations</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── Annual / Monthly toggle ────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6 pt-8 pb-4">
        <div className="flex items-center justify-center gap-3">
          <span className={`text-sm ${!annual ? 'text-white font-semibold' : 'text-gray-500'}`}>Monthly</span>
          <button
            onClick={() => setAnnual(!annual)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              annual ? 'bg-indigo-600' : 'bg-gray-700'
            }`}
          >
            <span
              className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                annual ? 'translate-x-6' : 'translate-x-0.5'
              }`}
            />
          </button>
          <span className={`text-sm ${annual ? 'text-white font-semibold' : 'text-gray-500'}`}>
            Annual <span className="text-green-400 text-xs">(save ~17%)</span>
          </span>
        </div>
      </div>

      {/* ── Plan cards ─────────────────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6 pb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
          {PLANS.map((plan) => {
            const isCurrent = plan.id === tier
            const isDemoTier = tier === 'demo' && plan.id === 'pro'
            const displayPrice = annual && plan.annualPrice ? plan.annualPrice : plan.price
            const displayPeriod = annual && plan.annualPeriod ? plan.annualPeriod : plan.period
            const Icon = plan.icon

            return (
              <div
                key={plan.id}
                className={`relative flex flex-col rounded-2xl border transition-all duration-200 ${
                  isCurrent
                    ? `${plan.borderColor} ring-1 ${plan.borderColor.replace('border', 'ring')}`
                    : plan.popular
                    ? 'border-indigo-500/50 hover:border-indigo-400'
                    : 'border-gray-800 hover:border-gray-700'
                } ${plan.bgColor}`}
              >
                {/* Popular badge */}
                {plan.popular && !isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full
                                  bg-indigo-600 text-white text-xs font-semibold shadow-lg">
                    MOST POPULAR
                  </div>
                )}

                {/* Current plan badge */}
                {isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full
                                  bg-green-600 text-white text-xs font-semibold shadow-lg">
                    CURRENT PLAN
                  </div>
                )}

                {/* Header */}
                <div className="p-6 pb-4">
                  <div className="flex items-center gap-2 mb-1">
                    {Icon && <Icon className={`w-5 h-5 ${plan.color}`} />}
                    <h3 className={`text-lg font-bold ${plan.color}`}>{plan.name}</h3>
                  </div>
                  <p className="text-xs text-gray-500 mb-4">{plan.tagline}</p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold">{displayPrice}</span>
                    <span className="text-sm text-gray-500">{displayPeriod}</span>
                  </div>
                  {annual && plan.annualPrice && (
                    <p className="text-xs text-green-400 mt-1">
                      vs {plan.price}{plan.period} — save ~17%
                    </p>
                  )}
                  <p className="text-xs text-gray-500 mt-3 leading-relaxed">{plan.description}</p>
                </div>

                {/* Features */}
                <div className="flex-1 px-6 pb-4 space-y-2.5">
                  {plan.features.map((feat, i) => (
                    <div key={i} className="flex items-start gap-2.5">
                      {feat.icon ? (
                        feat.icon === XIcon ? (
                          <XIcon className="w-4 h-4 text-gray-600 mt-0.5 shrink-0" />
                        ) : (
                          <feat.icon className={`w-4 h-4 ${
                            feat.highlight ? 'text-indigo-400' : 'text-green-400'
                          } mt-0.5 shrink-0`} />
                        )
                      ) : (
                        <div className={`w-4 h-4 mt-0.5 shrink-0 rounded-full flex items-center justify-center ${
                          feat.included ? 'bg-green-500/20' : 'bg-gray-800'
                        }`}>
                          {feat.included ? (
                            <Check className="w-3 h-3 text-green-400" />
                          ) : (
                            <XIcon className="w-3 h-3 text-gray-600" />
                          )}
                        </div>
                      )}
                      <span className={`text-xs leading-relaxed ${
                        feat.highlight ? 'text-white font-medium' : 'text-gray-400'
                      }`}>
                        {feat.text}
                      </span>
                    </div>
                  ))}
                </div>

                {/* CTA */}
                <div className="px-6 pb-6 mt-auto">
                  <button
                    onClick={() => !plan.disabled && handleSubscribe(
                      annual && plan.id === 'pro' ? 'price_pro_annual'
                      : annual && plan.id === 'enterprise' ? 'price_enterprise_annual'
                      : plan.priceId!,
                      plan.id,
                    )}
                    disabled={isCurrent || plan.disabled || (isDemoTier && plan.id === 'pro')}
                    className={`w-full py-2.5 rounded-xl font-semibold transition-all ${
                      isCurrent || (isDemoTier && plan.id === 'pro')
                        ? 'bg-gray-800 text-gray-400 cursor-not-allowed'
                        : plan.popular
                        ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20'
                        : 'bg-gray-800 hover:bg-gray-700 text-gray-200'
                    }`}
                  >
                    {isDemoTier && plan.id === 'pro' ? 'Try Pro (Demo Active)' : isCurrent ? 'Current Plan' : plan.cta}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Promo Code ─────────────────────────────────────────────── */}
      <div className="max-w-6xl mx-auto px-6 pb-12">
        <div className="p-6 rounded-2xl border border-gray-800 bg-gray-900/30">
          <h3 className="text-lg font-semibold mb-1">Have a promo code?</h3>
          <p className="text-sm text-gray-500 mb-4">Enter your code to unlock features or extend your trial.</p>
          <div className="flex gap-2 max-w-md">
            <input
              type="text"
              value={promoCode}
              onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
              placeholder="ENTER CODE"
              className="flex-1 px-4 py-2.5 rounded-xl bg-gray-800 border border-gray-700 text-white
                         placeholder-gray-600 font-mono tracking-wider text-sm
                         focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            <button
              onClick={handleRedeem}
              disabled={promoStatus === 'loading' || !promoCode.trim()}
              className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500
                         text-white font-semibold disabled:opacity-50 transition-colors"
            >
              {promoStatus === 'loading' ? 'Applying...' : 'Apply'}
            </button>
          </div>
          {promoStatus === 'success' && (
            <p className="mt-3 text-sm text-green-400 flex items-center gap-1.5">
              <Check className="w-4 h-4" /> {promoMessage}
            </p>
          )}
          {promoStatus === 'error' && (
            <p className="mt-3 text-sm text-red-400">❌ {promoMessage}</p>
          )}
        </div>
      </div>

      {/* ── FAQ ────────────────────────────────────────────────────── */}
      <div className="max-w-3xl mx-auto px-6 pb-16">
        <h3 className="text-lg font-semibold mb-4 text-center">Frequently Asked Questions</h3>
        <div className="space-y-3">
          {[
            { q: 'Can I cancel anytime?', a: 'Yes. No questions asked. Your jobs remain accessible until the end of the billing period.' },
            { q: 'What happens when my demo expires?', a: 'You become a Viewer — you keep access to shared reports but cannot create new simulations. Your existing jobs are preserved for 14 days.' },
            { q: 'Can I switch from monthly to annual?', a: 'Yes. Contact us or use the Stripe Customer Portal to switch. The annual plan saves ~17%.' },
            { q: 'Do you offer academic discounts?', a: 'Yes. Email us with your .edu address for a special academic rate.' },
            { q: 'Is my data secure?', a: 'All data is encrypted at rest. Enterprise tier offers on-premise deployment and SSO/SAML.' },
          ].map((faq, i) => (
            <details key={i} className="group">
              <summary className="cursor-pointer text-sm text-gray-300 hover:text-white font-medium py-2
                                     list-none flex items-center justify-between">
                {faq.q}
                <span className="text-gray-600 group-open:rotate-180 transition-transform">▼</span>
              </summary>
              <p className="text-sm text-gray-500 mt-1 pb-2">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
    </div>
  )
}
```

### 10d. Store modifications

In `web/frontend/src/store/authStore.ts`, add `tier`:

```ts
interface AuthState {
  token: string | null
  username: string | null
  tier: 'free' | 'pro' | 'enterprise'
  // ...
}

// When storing the token after login, extract tier from user info
```

In `web/frontend/src/api/client.ts`, add:

```ts
export const getSubscription = () =>
  http.get('/billing/subscription').then((r) => r.data)

export const createCheckoutSession = (priceId: string) =>
  http.post<{ url: string }>('/billing/create-checkout', { price_id: priceId }).then((r) => r.data)

export const getPortalUrl = () =>
  http.get<{ url: string }>('/billing/portal').then((r) => r.data)
```

In `web/frontend/src/pages/DashboardPage.tsx`, add the tier badge in the header:

```tsx
import TierBadge from '../components/TierBadge'

// In the header, next to the title:
<TierBadge tier={tier} />
```

---

## 11. Validation

After implementation, run these checks:

### Backend tests

```bash
# 1. Rate limiter
for i in $(seq 1 15); do
  curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/options | jq -r '.tier // error'
done
# After 10 requests, free tier should get 429

# 2. Job quota
# Try submitting 11 heatmap jobs as free user — 11th should fail

# 3. Tier validation
curl -s -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"mode":"orbit","params":{"sats":100,"planes":10,"altitude":600,"inclination":87}}'
# Free tier should be blocked from orbit mode

# 4. Watermark
# Submit a heatmap as free user, download the PNG, check for watermark text

# 5. Stripe webhook
# Use Stripe CLI to trigger test events:
# stripe trigger customer.subscription.created

# 6. Cleanup
# Manually run the cleanup function and verify old jobs are removed
```

### Stripe CLI test flow

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe login
stripe listen --forward-to localhost:8000/api/billing/webhook

# In another terminal:
stripe trigger customer.subscription.created
# Check that the user's tier was updated in the database
```

### Expected DB state after successful subscription

```sql
SELECT username, tier, subscription_status, stripe_customer_id
FROM users;

-- Result:
-- admin      | enterprise | active       | cus_xxx
-- testuser   | pro        | active       | cus_yyy
```

---

## Implementation Order

| Order | Module | Est. time | Dependencies |
|-------|--------|-----------|--------------|
| 1 | `db.py` | 30 min | None (stdlib SQLite) |
| 2 | `tier_config.py` | 20 min | None |
| 3 | `config.py` additions | 5 min | None |
| 4 | `auth.py` additions (decode_token_from_request + tier in JWT) | 15 min | `db.py` |
| 5 | `rate_limiter.py` | 30 min | `auth.py`, `tier_config.py` |
| 6 | Jobs routes validation | 20 min | `db.py`, `tier_config.py` |
| 7 | Options route tier filter | 10 min | `tier_config.py` |
| 8 | `stripe_integration.py` | 60 min | `db.py`, `tier_config.py` |
| 9 | `watermark.py` | 20 min | Pillow (add to requirements.txt) |
| 10 | Worker env vars + watermark hook | 15 min | `watermark.py` |
| 11 | `cleanup.py` | 15 min | `db.py`, `tier_config.py` |
| 12 | Frontend: TierBadge | 10 min | None |
| 13 | Frontend: UpgradeModal | 30 min | API client |
| 14 | Frontend: BillingPage | 45 min | API client |
| 15 | Frontend: Dashboard integration | 15 min | TierBadge + UpgradeModal |
| 16 | Test & debug | 45 min | All |
| **Total** | | **~6.5 hours** | |

---

## 12. Promo Codes (Bonus Feature)

### Overview

A lightweight promo code system that allows:
- **Time-limited tier unlocks**: "Try Pro for 7 days" — user enters code → tier upgraded for N days
- **Feature unlocks**: "Unlock AI analysis for 20 simulations" without changing tier
- **Stripe coupon passthrough**: Generate a Stripe coupon and tie it to a discount code
- **One-time or multi-use**: Codes can be single-use per user, global limited, or unlimited

**Complexity:** Low (~200 lines backend, ~30 lines frontend)

### DB Schema

Add to `db.py` `init_db()`:

```python
conn.executescript("""
    CREATE TABLE IF NOT EXISTS promo_codes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        code            TEXT    UNIQUE NOT NULL,
        description     TEXT    DEFAULT '',
        reward_type     TEXT    NOT NULL DEFAULT 'trial_upgrade',
            -- 'trial_upgrade':  upgrade tier for N days
            -- 'feature_unlock': unlock specific features
            -- 'stripe_coupon':  maps to a Stripe coupon ID
        reward_value    TEXT    NOT NULL,
            -- for 'trial_upgrade': "pro|7"  (tier|days)
            -- for 'feature_unlock': "ai_analysis:20,latency:1"  (feature:count,...)
            -- for 'stripe_coupon': stripe coupon ID like "FRIENDS20"
        max_uses        INTEGER DEFAULT 1,     -- total times this code can be used globally
        max_uses_per_user INTEGER DEFAULT 1,    -- times per user
        expires_at      TEXT,                   -- ISO datetime or NULL (never)
        is_active       INTEGER DEFAULT 1,
        created_by      TEXT    DEFAULT 'admin',
        created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
        used_count      INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS redeemed_codes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        username        TEXT    NOT NULL,
        code_id         INTEGER NOT NULL,
        reward_type     TEXT    NOT NULL,
        reward_value    TEXT    NOT NULL,
        expires_at      TEXT,                   -- when this reward expires (for time-limited)
        redeemed_at     TEXT    NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (code_id) REFERENCES promo_codes(id)
    );

    CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);
    CREATE INDEX IF NOT EXISTS idx_redeemed_username ON redeemed_codes(username);
""")
```

### Functions in `db.py`

```python
def get_promo_code(outputs_dir: Path, code: str) -> Optional[dict]:
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM promo_codes WHERE code = ? AND is_active = 1",
        (code.upper(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_redemptions(outputs_dir: Path, username: str, code_id: int) -> list:
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM redeemed_codes WHERE username = ? AND code_id = ?",
        (username, code_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def redeem_code(outputs_dir: Path, username: str, code_id: int,
                reward_type: str, reward_value: str, expires_at: Optional[str] = None):
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO redeemed_codes
           (username, code_id, reward_type, reward_value, expires_at, redeemed_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (username, code_id, reward_type, reward_value, expires_at, now),
    )
    conn.execute(
        "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?",
        (code_id,),
    )
    conn.commit()
    conn.close()


def create_promo_code(outputs_dir: Path, code: str, reward_type: str,
                      reward_value: str, max_uses: int = 1,
                      max_uses_per_user: int = 1,
                      expires_at: Optional[str] = None) -> dict:
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """INSERT INTO promo_codes
           (code, reward_type, reward_value, max_uses, max_uses_per_user, expires_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (code.upper(), reward_type, reward_value, max_uses, max_uses_per_user, expires_at),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM promo_codes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def list_promo_codes(outputs_dir: Path) -> list[dict]:
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM promo_codes ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

### Validation Logic (in `tier_config.py` or new `promo.py`)

```python
"""
web/backend/app/promo.py — Promo code validation and redemption.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional


def validate_promo_code(outputs_dir: Path, code: str, username: str) -> dict:
    """
    Validate a promo code and return its details.

    Returns dict with:
      - valid: bool
      - error: str (if invalid)
      - reward_type: str
      - reward_value: str
      - expires_at: str (ISO, when the reward itself expires)

    Error cases:
      - Code not found
      - Code expired
      - Code max uses reached
      - User already redeemed this code
      - User already has an active trial of the same type
    """
    from .db import get_promo_code, get_user_redemptions

    promo = get_promo_code(outputs_dir, code)
    if not promo:
        return {"valid": False, "error": "Invalid promo code"}

    now = datetime.now(timezone.utc)

    # Check expiry
    if promo.get("expires_at"):
        exp = datetime.fromisoformat(promo["expires_at"])
        if now > exp:
            return {"valid": False, "error": "This promo code has expired"}

    # Check global max uses
    if promo["max_uses"] > 0 and promo["used_count"] >= promo["max_uses"]:
        return {"valid": False, "error": "This promo code has reached its usage limit"}

    # Check per-user max uses
    user_redeems = get_user_redemptions(outputs_dir, username, promo["id"])
    if len(user_redeems) >= promo["max_uses_per_user"]:
        return {"valid": False, "error": "You have already used this promo code"}

    # Parse reward value and compute expiry
    reward_type = promo["reward_type"]
    reward_value = promo["reward_value"]
    reward_expires_at = None

    if reward_type == "trial_upgrade":
        # Format: "pro|7"  → upgrade to pro for 7 days
        parts = reward_value.split("|")
        if len(parts) == 2:
            days = int(parts[1])
            reward_expires_at = (now + timedelta(days=days)).isoformat()

    return {
        "valid": True,
        "error": None,
        "promo_id": promo["id"],
        "reward_type": reward_type,
        "reward_value": reward_value,
        "expires_at": reward_expires_at,
    }


def apply_promo_reward(outputs_dir: Path, username: str,
                       promo_id: int, reward_type: str,
                       reward_value: str, expires_at: Optional[str] = None):
    """
    Apply the reward from a promo code to a user.

    For 'trial_upgrade': upgrade user's tier temporarily.
    For 'feature_unlock': store feature-specific overrides.

    This function handles both the DB record AND the side effect on the user.
    """
    from .db import redeem_code, get_user_by_username, update_user_tier

    now = datetime.now(timezone.utc)

    if reward_type == "trial_upgrade":
        # Format: "pro|7"
        tier = reward_value.split("|")[0]
        db_user = get_user_by_username(outputs_dir, username)

        # If user is already on a higher tier, don't downgrade them
        current_tier = db_user["tier"] if db_user else "free"
        tier_rank = {"free": 0, "pro": 1, "enterprise": 2}
        if tier_rank.get(tier, 0) > tier_rank.get(current_tier, 0):
            update_user_tier(
                outputs_dir, username, tier,
                subscription_status=f"trial_{tier}",
            )
            # Store the trial expiry in the user record
            conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
            conn.execute(
                "UPDATE users SET updated_at = ? WHERE username = ?",
                (now.isoformat(), username),
            )
            conn.close()

    # Record the redemption
    redeem_code(outputs_dir, username, promo_id, reward_type, reward_value, expires_at)
```

### Admin API Routes

Add to `web/backend/app/api/billing_routes.py` (or a new `promo_routes.py`):

```python
from ..db import create_promo_code, list_promo_codes
from ..promo import validate_promo_code, apply_promo_reward


@router.post("/promo-codes")
async def admin_create_promo(
    body: PromoCodeCreate,
    user: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Admin-only: create a new promo code."""
    if not _is_admin(user, settings):
        raise HTTPException(status_code=403, detail="Admin only")
    promo = create_promo_code(
        settings.outputs_dir,
        code=body.code,
        reward_type=body.reward_type,
        reward_value=body.reward_value,
        max_uses=body.max_uses,
        max_uses_per_user=body.max_uses_per_user,
        expires_at=body.expires_at,
    )
    return promo


@router.get("/promo-codes")
async def admin_list_promos(
    user: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Admin-only: list all promo codes."""
    if not _is_admin(user, settings):
        raise HTTPException(status_code=403, detail="Admin only")
    return list_promo_codes(settings.outputs_dir)


@router.post("/redeem")
async def redeem_promo(
    body: RedeemRequest,
    user: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """User redeems a promo code."""
    # Validate
    validation = validate_promo_code(settings.outputs_dir, body.code, user)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])

    # Apply
    apply_promo_reward(
        settings.outputs_dir,
        user,
        promo_id=validation["promo_id"],
        reward_type=validation["reward_type"],
        reward_value=validation["reward_value"],
        expires_at=validation.get("expires_at"),
    )

    return {
        "success": True,
        "message": f"Promo code applied! {_reward_message(validation)}",
        "reward_type": validation["reward_type"],
    }


def _is_admin(username: str, settings) -> bool:
    return username == settings.admin_username


def _reward_message(validation: dict) -> str:
    rt = validation["reward_type"]
    rv = validation["reward_value"]
    if rt == "trial_upgrade":
        tier, days = rv.split("|")
        return f"Upgraded to {tier.title()} for {days} days!"
    if rt == "feature_unlock":
        return f"Features unlocked: {rv}"
    return "Reward applied!"


# ── Request models ──────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import Optional


class PromoCodeCreate(BaseModel):
    code: str = Field(..., min_length=3, max_length=32)
    description: str = ""
    reward_type: str = Field(..., pattern=r"^(trial_upgrade|feature_unlock|stripe_coupon)$")
    reward_value: str = Field(..., max_length=128)
    max_uses: int = 1
    max_uses_per_user: int = 1
    expires_at: Optional[str] = None


class RedeemRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
```

### Example Promo Codes (for seeding)

```python
SEED_CODES = [
    {
        "code": "WELCOME7",
        "description": "7-day free Pro trial for new users",
        "reward_type": "trial_upgrade",
        "reward_value": "pro|7",
        "max_uses": 1000,
        "max_uses_per_user": 1,
    },
    {
        "code": "LAUNCH2026",
        "description": "30-day Enterprise trial (launch promo)",
        "reward_type": "trial_upgrade",
        "reward_value": "enterprise|30",
        "max_uses": 50,
        "max_uses_per_user": 1,
        "expires_at": "2026-12-31T23:59:59Z",
    },
    {
        "code": "AI20",
        "description": "Unlock 20 AI analyses on any tier",
        "reward_type": "feature_unlock",
        "reward_value": "ai_analysis:20",
        "max_uses": 500,
        "max_uses_per_user": 1,
    },
    {
        "code": "STUDENT50",
        "description": "50 free simulations for students",
        "reward_type": "feature_unlock",
        "reward_value": "extra_jobs:50",
        "max_uses": 200,
        "max_uses_per_user": 1,
    },
]
```

### Frontend: Promo Code Input

Add to `web/frontend/src/pages/BillingPage.tsx`:

```tsx
// ── Promo Code Section ──────────────────────────────────────────────────────
const [promoCode, setPromoCode] = useState('')
const [promoStatus, setPromoStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
const [promoMessage, setPromoMessage] = useState('')

const handleRedeem = async () => {
  if (!promoCode.trim()) return
  setPromoStatus('loading')
  try {
    const result = await axios.post('/api/billing/redeem', { code: promoCode.trim() })
    setPromoStatus('success')
    setPromoMessage(result.data.message)
    setPromoCode('')
    // Refresh user data to reflect new tier
    // window.location.reload()
  } catch (err: any) {
    setPromoStatus('error')
    setPromoMessage(err.response?.data?.detail || 'Invalid code')
  }
}

// Add this somewhere in the billing page, after the plan cards:
<div className="mt-8 p-6 rounded-xl border border-gray-800 bg-gray-900">
  <h3 className="text-lg font-semibold mb-2">Have a promo code?</h3>
  <div className="flex gap-2">
    <input
      type="text"
      value={promoCode}
      onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
      placeholder="Enter code"
      className="flex-1 px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white
                 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
    />
    <button
      onClick={handleRedeem}
      disabled={promoStatus === 'loading' || !promoCode.trim()}
      className="px-6 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500
                 text-white font-semibold disabled:opacity-50 transition-colors"
    >
      {promoStatus === 'loading' ? 'Applying...' : 'Apply'}
    </button>
  </div>
  {promoStatus === 'success' && (
    <p className="mt-2 text-sm text-green-400">✅ {promoMessage}</p>
  )}
  {promoStatus === 'error' && (
    <p className="mt-2 text-sm text-red-400">❌ {promoMessage}</p>
  )}
</div>
```

### Admin: Manage Promo Codes

Add an admin panel section in `SettingsPage.tsx` or a new `AdminPage.tsx`:

```tsx
// Admin-only: list, create, toggle promo codes
// Protected by checking username === admin
```

### Use Cases

| Scenario | Code | Effect |
|----------|------|--------|
| Onboarding trial | `WELCOME7` | Free tier → Pro por 7 dias |
| Launch promo | `LAUNCH2026` | Qualquer tier → Enterprise por 30 dias |
| AI sampler | `AI20` | Ganha 20 análises AI extra (mesmo em Free) |
| Student/educator | `STUDENT50` | 50 simulações extra |
| Partner referral | `PARTNER100` | Pro por 100 dias |
| Conference | `SATELLITE2026` | Pro por 14 dias (uso único por email) |

### Security Considerations

1. **Codes are case-insensitive** — stored as uppercase, compared uppercase
2. **Rate limit redemption attempts** — max 5 attempts per minute per user (reuses the rate limiter)
3. **Audit trail** — `redeemed_codes` table logs who redeemed what, when
4. **Trial cannot extend** — if user is already on Pro trial, applying another Pro trial code does nothing (check in `apply_promo_reward`)
5. **Stripe coupon passthrough** — for `stripe_coupon` type, the frontend shows the coupon code to apply at Stripe Checkout, rather than modifying the local DB

### Implementation Effort

| Piece | Lines | Time |
|-------|-------|------|
| DB schema + functions | ~50 | 15 min |
| Validation logic | ~60 | 15 min |
| Admin API routes | ~40 | 10 min |
| Redemption API route | ~30 | 10 min |
| Frontend input | ~40 | 15 min |
| Seed codes | ~20 | 5 min |
| **Total** | **~240** | **~70 min** |

---

## Dependencies to add

### `web/backend/requirements.txt`

```
stripe>=7.0.0
Pillow>=10.0.0
```

(Everything else is Python stdlib: `sqlite3`, `json`, `time`, `collections.deque`, etc.)

### `web/frontend/package.json`

No new dependencies — using existing `lucide-react` for icons, existing Tailwind for styling.

---

## Potential Pitfalls

1. **SQLite concurrency**: The RQ worker and API server may access the DB simultaneously. SQLite's WAL mode handles this for low concurrency. If scaling beyond ~10 concurrent users, switch to PostgreSQL.

2. **Stripe webhook idempotency**: The `stripe_events` table ensures each event is processed exactly once. Important for `customer.subscription.updated` which may fire multiple times.

3. **Job quota reset**: The `current_month` column tracks which month the counter applies to. When comparing `strftime('%Y-%m', 'now')`, ensure the comparison handles year boundaries correctly (it does — string comparison of '2026-01' < '2026-02' works lexicographically).

4. **Watermark on GIFs/HTML**: The watermark function only handles PNG/JPEG. HTML (Plotly) and GIF outputs are not watermarked in this implementation. For GIFs, consider adding a watermark frame by frame if needed.

5. **Docker rebuild**: After modifying Python dependencies (`requirements.txt`), the Docker images need rebuilding:
   ```bash
   cd web/
   docker compose build api worker
   docker compose up -d
   ```

6. **Stripe test mode**: Use `sk_test_...` keys during development. The Stripe webhook requires a public URL — use `stripe listen --forward-to` for local testing or deploy to a staging server with HTTPS.

7. **Enterprise pricing**: €999/mês is a "starting from" price. Real enterprise contracts would be negotiated case-by-case. Consider adding a `/api/billing/contact-sales` endpoint that sends an email to the admin.
