"""
Tests for RBAC permission matrix and role hierarchy.

Run: python -m pytest tests/test_rbac.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web", "backend"))

import pytest
from datetime import datetime, timezone
from app.rbac import (
    ROLE_HIERARCHY, PERMISSIONS, has_permission, role_is_at_least,
    demo_is_expired, get_effective_role,
)


class TestRoleHierarchy:
    """Verify role hierarchy levels."""

    def test_hierarchy_order(self):
        assert ROLE_HIERARCHY["demo"] < ROLE_HIERARCHY["viewer"]
        assert ROLE_HIERARCHY["viewer"] < ROLE_HIERARCHY["creator"]
        assert ROLE_HIERARCHY["creator"] < ROLE_HIERARCHY["team_manager"]
        assert ROLE_HIERARCHY["team_manager"] < ROLE_HIERARCHY["admin"]

    @pytest.mark.parametrize("role,min_role,expected", [
        ("admin", "viewer", True),
        ("admin", "admin", True),
        ("viewer", "admin", False),
        ("creator", "viewer", True),
        ("viewer", "creator", False),
    ])
    def test_role_is_at_least(self, role, min_role, expected):
        assert role_is_at_least(role, min_role) is expected


class TestPermissions:
    """Verify each role has correct permissions."""

    ADMIN_PERMS = [
        "users:manage", "users:view_all", "orgs:manage",
        "jobs:create", "jobs:delete_any", "settings:write",
        "billing:manage", "admin:panel",
    ]
    VIEWER_FORBIDDEN = ["jobs:create", "users:manage", "billing:manage"]

    @pytest.mark.parametrize("perm", ADMIN_PERMS)
    def test_admin_has_all_permissions(self, perm):
        assert has_permission("admin", perm) is True

    @pytest.mark.parametrize("perm", VIEWER_FORBIDDEN)
    def test_viewer_missing_critical_perms(self, perm):
        assert has_permission("viewer", perm) is False

    def test_creator_can_create_jobs(self):
        assert has_permission("creator", "jobs:create") is True
        assert has_permission("creator", "jobs:delete_own") is True

    def test_creator_cannot_manage_users(self):
        assert has_permission("creator", "users:manage") is False

    def test_team_manager_can_view_team_jobs(self):
        assert has_permission("team_manager", "jobs:view_team") is True
        assert has_permission("team_manager", "jobs:delete_team") is True
        assert has_permission("team_manager", "users:manage") is True

    def test_viewer_can_view_shared_reports(self):
        assert has_permission("viewer", "reports:view_shared") is True

    def test_unknown_role_has_no_permissions(self):
        assert has_permission("nonexistent", "jobs:create") is False
        assert has_permission("nonexistent", "admin:panel") is False


class TestDemoExpiry:
    """Verify demo user lifecycle logic."""

    def test_demo_not_expired_fresh(self):
        from datetime import timedelta
        user = {
            "role": "demo",
            "demo_expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "demo_jobs_limit": 10,
            "demo_jobs_used": 0,
        }
        assert demo_is_expired(user) is False

    def test_demo_expired_by_jobs(self):
        user = {
            "role": "demo",
            "demo_expires_at": (datetime.now(timezone.utc)).isoformat(),
            "demo_jobs_limit": 10,
            "demo_jobs_used": 10,
        }
        assert demo_is_expired(user) is True

    def test_demo_expired_by_time(self):
        from datetime import timedelta
        user = {
            "role": "demo",
            "demo_expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "demo_jobs_limit": 10,
            "demo_jobs_used": 0,
        }
        assert demo_is_expired(user) is True

    def test_non_demo_never_expired(self):
        user = {"role": "creator", "demo_expires_at": None}
        assert demo_is_expired(user) is False

    def test_effective_role_demotes_expired_demo(self):
        user = {
            "role": "demo",
            "demo_expires_at": "2020-01-01T00:00:00Z",
            "demo_jobs_limit": 10,
            "demo_jobs_used": 0,
        }
        assert get_effective_role(user) == "viewer"

    def test_effective_role_keeps_active_demo(self):
        user = {
            "role": "demo",
            "demo_expires_at": "2099-01-01T00:00:00Z",
            "demo_jobs_limit": 10,
            "demo_jobs_used": 0,
        }
        assert get_effective_role(user) == "demo"
