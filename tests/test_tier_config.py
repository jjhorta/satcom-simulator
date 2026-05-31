"""
Tests for tier_config.py — TIER_LIMITS, role mappings, and job param validation.

Run: python -m pytest tests/test_tier_config.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web", "backend"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.tier_config import (
    TIER_LIMITS, SUBSCRIPTION_MAX_ROLE, STRIPE_PRICES,
    get_limits, role_max_from_subscription, mode_allowed, validate_job_params,
)


class TestTierLimits:
    """Verify every role has all required keys in TIER_LIMITS."""

    REQUIRED_KEYS = [
        "max_sats", "max_planes", "modes", "jobs_per_month",
        "concurrent_jobs", "export_formats", "retention_days",
        "multi_shell", "watermark", "can_create_jobs",
    ]

    @pytest.mark.parametrize("role", ["viewer", "demo", "creator", "team_manager", "admin"])
    def test_role_has_all_keys(self, role):
        limits = TIER_LIMITS.get(role)
        assert limits is not None, f"Role '{role}' missing from TIER_LIMITS"
        for key in self.REQUIRED_KEYS:
            assert key in limits, f"Role '{role}' missing key '{key}'"

    def test_viewer_can_create_limited_jobs(self):
        limits = get_limits("viewer")
        assert limits["can_create_jobs"] is True
        assert limits["max_jobs_total"] == 3
        assert limits["jobs_per_month"] == 3

    def test_demo_has_limits(self):
        limits = get_limits("demo")
        assert limits["max_jobs_total"] == 10
        assert limits["jobs_per_month"] == 10
        assert limits["multi_shell"] is True

    def test_creator_monthly_quota(self):
        limits = get_limits("creator")
        assert limits["jobs_per_month"] == 500
        assert limits["concurrent_jobs"] == 3
        assert limits["watermark"] is False

    def test_admin_is_unlimited(self):
        limits = get_limits("admin")
        assert limits["jobs_per_month"] == -1
        assert limits["concurrent_jobs"] == 50
        assert limits["multi_shell"] is True

    def test_unknown_role_falls_back_to_viewer(self):
        limits = get_limits("nonexistent")
        assert limits["can_create_jobs"] is True  # viewer has 3 trials
        assert limits["max_jobs_total"] == 3


class TestSubscriptionMaxRole:
    """Verify SUBSCRIPTION_MAX_ROLE mappings."""

    @pytest.mark.parametrize("tier,expected_role", [
        ("free", "viewer"),
        ("pro", "creator"),
        ("enterprise", "team_manager"),
    ])
    def test_tier_maps_to_role(self, tier, expected_role):
        assert SUBSCRIPTION_MAX_ROLE[tier] == expected_role

    def test_unknown_tier_falls_back(self):
        assert role_max_from_subscription("unknown") == "viewer"


class TestModeAllowed:
    """Verify which simulation modes each role can access."""

    def test_viewer_only_heatmap(self):
        assert mode_allowed("viewer", "heatmap") is True
        assert mode_allowed("viewer", "orbit") is False
        assert mode_allowed("viewer", "sky") is False

    def test_creator_has_full_set(self):
        for mode in ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route"]:
            assert mode_allowed("creator", mode) is True, f"creator should have '{mode}'"

    def test_team_manager_has_latency(self):
        assert mode_allowed("team_manager", "latency") is True

    def test_viewer_no_latency(self):
        assert mode_allowed("viewer", "latency") is False


class TestValidateJobParams:
    """Verify job parameter validation against role limits."""

    def test_viewer_3_sats_ok(self):
        errors = validate_job_params("viewer", {"sats": 3, "planes": 1, "mode": "heatmap"})
        assert len(errors) == 0

    def test_viewer_too_many_sats(self):
        errors = validate_job_params("viewer", {"sats": 999, "planes": 1, "mode": "heatmap"})
        assert any("Max satellites" in e for e in errors)

    def test_viewer_wrong_mode(self):
        errors = validate_job_params("viewer", {"sats": 3, "planes": 1, "mode": "orbit"})
        assert any("not available" in e for e in errors)

    def test_creator_250_sats_ok(self):
        errors = validate_job_params("creator", {"sats": 250, "planes": 72, "mode": "orbit"})
        assert len(errors) == 0

    def test_creator_exceeds_sats(self):
        errors = validate_job_params("creator", {"sats": 251, "planes": 1, "mode": "heatmap"})
        assert any("Max satellites" in e for e in errors)

    def test_demo_cannot_use_latency(self):
        errors = validate_job_params("demo", {"sats": 10, "planes": 2, "mode": "latency"})
        assert any("not available" in e for e in errors)

    def test_admin_everything_allowed(self):
        errors = validate_job_params("admin", {"sats": 99999, "planes": 999, "mode": "latency", "duration": 10080})
        assert len(errors) == 0


class TestStripePrices:
    """Verify Stripe price definitions."""

    def test_pro_monthly_price(self):
        assert STRIPE_PRICES["pro_monthly"]["amount_cents"] == 29900
        assert STRIPE_PRICES["pro_monthly"]["currency"] == "eur"

    def test_pro_annual_discount(self):
        monthly = STRIPE_PRICES["pro_monthly"]["amount_cents"] * 12
        annual = STRIPE_PRICES["pro_annual"]["amount_cents"]
        assert annual < monthly, "Annual should be cheaper than 12x monthly"
        assert monthly - annual > 0, "Annual should have a discount"

    def test_enterprise_monthly_price(self):
        assert STRIPE_PRICES["enterprise_monthly"]["amount_cents"] == 99900
