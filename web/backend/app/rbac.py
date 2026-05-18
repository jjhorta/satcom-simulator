"""
web/backend/app/rbac.py — Role definitions, permission matrix, and helpers.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

# ── Role hierarchy (higher number = more privileges) ─────────────────────────
ROLE_HIERARCHY: dict[str, int] = {
    "demo":         0,
    "viewer":       1,
    "creator":      2,
    "team_manager": 3,
    "admin":        4,
}

# ── Permission matrix ─────────────────────────────────────────────────────────
PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "users:manage",
        "users:view_all",
        "orgs:manage",
        "orgs:view_all",
        "jobs:create",
        "jobs:view_own",
        "jobs:view_team",
        "jobs:delete_own",
        "jobs:delete_any",
        "settings:read",
        "settings:write",
        "billing:manage",
        "billing:view",
        "reports:share",
        "reports:view_all",
        "api:access",
        "admin:panel",
    },
    "team_manager": {
        "users:manage",
        "users:view_team",
        "orgs:view_own",
        "jobs:create",
        "jobs:view_own",
        "jobs:view_team",
        "jobs:delete_own",
        "jobs:delete_team",
        "settings:read",
        "billing:view",
        "reports:share",
        "reports:view_team",
        "api:access",
    },
    "creator": {
        "jobs:create",
        "jobs:view_own",
        "jobs:delete_own",
        "settings:read",
        "reports:share",
        "api:access",
    },
    "viewer": {
        "jobs:view_own",
        "reports:view_shared",
        "settings:read",
        "api:access",
    },
    "demo": {
        "jobs:create",
        "jobs:view_own",
        "settings:read",
        "reports:share",
        "api:access",
    },
}


def has_permission(role: str, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def role_is_at_least(user_role: str, minimum_role: str) -> bool:
    user_level = ROLE_HIERARCHY.get(user_role, -1)
    min_level  = ROLE_HIERARCHY.get(minimum_role, 0)
    return user_level >= min_level


def demo_is_expired(user: dict) -> bool:
    if user.get("role") != "demo":
        return False
    expires = user.get("demo_expires_at")
    if expires:
        try:
            exp = datetime.fromisoformat(expires)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                return True
        except ValueError:
            pass
    if (user.get("demo_jobs_limit", 10) or 10) <= (user.get("demo_jobs_used", 0) or 0):
        return True
    return False


def get_effective_role(user: dict) -> str:
    if user.get("role") == "demo" and demo_is_expired(user):
        return "viewer"
    return user["role"]
