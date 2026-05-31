"""
web/backend/app/tier_config.py — Tier definitions and feature flag resolution.

This file maps RBAC roles to feature limits. The pricing tier is stored on the
organization (organizations.subscription_tier), but the source of truth for
permissions is the user's role column (set by RBAC).

When a subscription updates, the Stripe webhook:
  1. Updates organizations.subscription_tier
  2. Promotes members to the max role allowed by their new tier
"""

from __future__ import annotations
from typing import Optional


# ── Map subscription tier → maximum RBAC role allowed ───────────────────────
# The team_manager can assign roles up to this level.
SUBSCRIPTION_MAX_ROLE: dict[str, str] = {
    "free":       "viewer",         # free orgs: read-only
    "pro":        "creator",        # pro orgs: creators who can simulate
    "enterprise": "team_manager",   # enterprise: full team management
}


# ── Map RBAC role → feature limits ──────────────────────────────────────────
# Role determines limits. get_limits(role) is the main lookup function.
TIER_LIMITS: dict[str, dict] = {
    "viewer": {
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
        "watermark": True,
        "tco_analysis": False,
        "latency_mode": True,
        "max_shells": 1,
        "can_create_jobs": True,
        "max_jobs_total": 3,
        "batch_sweep": False,
        "max_sweep_combinations": 0,
        "max_batch_jobs_per_month": 0,
    },
    "demo": {
        "max_sats": 250,
        "max_planes": 72,
        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route", "latency"],
        "heatmap_resolution": 2.0,
        "jobs_per_month": 10,
        "concurrent_jobs": 1,
        "max_duration_min": 1440,
        "export_formats": ["png", "csv", "gif", "html"],
        "ai_analyses_per_month": 3,
        "retention_days": 14,
        "backends": ["matplotlib", "plotly"],
        "multi_shell": True,
        "watermark": False,
        "tco_analysis": True,
        "latency_mode": True,
        "max_shells": 3,
        "can_create_jobs": True,
        "max_jobs_total": 10,
        "batch_sweep": False,
        "max_sweep_combinations": 0,
        "max_batch_jobs_per_month": 0,
    },
    "creator": {
        "max_sats": 250,
        "max_planes": 72,
        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route", "latency"],
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
        "latency_mode": True,
        "max_shells": 5,
        "can_create_jobs": True,
        "max_jobs_total": -1,
        "batch_sweep": True,
        "max_sweep_combinations": 50,
        "max_batch_jobs_per_month": 5,
    },
    "team_manager": {
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
        "batch_sweep": True,
        "max_sweep_combinations": 200,
        "max_batch_jobs_per_month": 20,
    },
    "admin": {
        "max_sats": 99999,
        "max_planes": 999,
        "modes": ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route", "latency"],
        "heatmap_resolution": 0.5,
        "jobs_per_month": -1,
        "concurrent_jobs": 50,
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
        "batch_sweep": True,
        "max_sweep_combinations": 500,
        "max_batch_jobs_per_month": 100,
    },
}

STRIPE_PRICES: dict[str, dict] = {
    "pro_monthly": {
        "id": "price_pro_monthly",
        "amount_cents": 29900,
        "currency": "eur",
        "interval": "month",
        "tier": "pro",
    },
    "pro_annual": {
        "id": "price_pro_annual",
        "amount_cents": 299000,
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


def get_limits(role: str) -> dict:
    """Return the limits dict for a given RBAC role. Falls back to 'viewer'."""
    return TIER_LIMITS.get(role, TIER_LIMITS["viewer"])


def role_max_from_subscription(subscription_tier: str) -> str:
    """What's the max RBAC role this subscription tier allows?"""
    return SUBSCRIPTION_MAX_ROLE.get(subscription_tier, "viewer")


def mode_allowed(role: str, mode: str) -> bool:
    """Check if a simulation mode is available for this role."""
    limits = get_limits(role)
    return mode in limits.get("modes", [])


def validate_job_params(role: str, params: dict) -> list[str]:
    """Validate job parameters against role limits. Returns list of error messages."""
    limits = get_limits(role)
    errors: list[str] = []

    if not limits.get("can_create_jobs", False):
        errors.append(f"Role '{role}' does not allow creating simulations.")
        return errors

    sats = params.get("sats", 0)
    if sats > limits["max_sats"]:
        errors.append(f"Max satellites for {role}: {limits['max_sats']} (requested: {sats})")

    planes = params.get("planes", 0)
    if planes > limits["max_planes"]:
        errors.append(f"Max planes for {role}: {limits['max_planes']} (requested: {planes})")

    duration = params.get("duration", 0)
    if duration > limits["max_duration_min"]:
        errors.append(f"Max duration for {role}: {limits['max_duration_min']} min (requested: {duration})")

    shells = params.get("shells", None)
    if shells and not limits["multi_shell"]:
        errors.append("Multi-shell is not available on this tier")
    if shells and isinstance(shells, list) and len(shells) > limits["max_shells"]:
        errors.append(f"Max {limits['max_shells']} shells allowed on {role} tier")

    mode = params.get("mode", "")
    if mode and not mode_allowed(role, mode):
        errors.append(f"Mode '{mode}' is not available on the {role} tier")

    return errors
