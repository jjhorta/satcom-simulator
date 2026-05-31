"""
Tests for job quota validation and RBAC permission enforcement in jobs_routes.

Run: python -m pytest tests/test_quotas.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web", "backend"))

import pytest
from app.rbac import has_permission, get_effective_role
from app.tier_config import get_limits, validate_job_params, mode_allowed


class TestJobCreationPermission:
    """Verify who can create simulations."""

    @pytest.mark.parametrize("role,expected", [
        ("viewer", False),    # 3 trials enforced by quota, not RBAC
        ("demo", True),
        ("creator", True),
        ("team_manager", True),
        ("admin", True),
    ])
    def test_can_create_jobs(self, role, expected):
        assert has_permission(role, "jobs:create") is expected


class TestConcurrentJobLimits:
    """Verify concurrent job limits per role."""

    @pytest.mark.parametrize("role,expected", [
        ("viewer", 1),
        ("demo", 1),
        ("creator", 3),
        ("team_manager", 10),
        ("admin", 50),
    ])
    def test_concurrent_limits(self, role, expected):
        limits = get_limits(role)
        assert limits["concurrent_jobs"] == expected


class TestMonthlyJobQuotas:
    """Verify monthly job quotas per role."""

    @pytest.mark.parametrize("role,expected_limit,description", [
        ("viewer", 3, "3 trials"),
        ("demo", 10, "10 demo jobs"),
        ("creator", 500, "500 jobs/mo"),
        ("team_manager", -1, "unlimited"),
        ("admin", -1, "unlimited"),
    ])
    def test_monthly_quotas(self, role, expected_limit, description):
        limits = get_limits(role)
        assert limits["jobs_per_month"] == expected_limit, f"{role}: {description}"


class TestMaxSatelliteLimits:
    """Verify max satellites per role."""

    @pytest.mark.parametrize("role,expected", [
        ("viewer", 24),
        ("demo", 250),
        ("creator", 250),
        ("team_manager", 99999),
        ("admin", 99999),
    ])
    def test_max_sats(self, role, expected):
        limits = get_limits(role)
        assert limits["max_sats"] == expected


class ViewModeAvailability:
    """Verify mode availability for each role."""

    def test_viewer_has_heatmap(self):
        assert mode_allowed("viewer", "heatmap") is True
        assert mode_allowed("viewer", "orbit") is False
        assert mode_allowed("viewer", "sky") is False

    def test_creator_has_all_basic_modes(self):
        modes = ["heatmap", "heatmap-rf", "sky", "orbit", "track", "route"]
        for m in modes:
            assert mode_allowed("creator", m) is True, f"creator should have mode '{m}'"

    def test_team_manager_has_latency(self):
        assert mode_allowed("team_manager", "latency") is True
