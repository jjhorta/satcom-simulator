"""
web/backend/app/deps.py — FastAPI dependency injection for authorization.

Usage:
    @router.get("/admin/users")
    async def list_users(
        _: None = Depends(require_permission("users:view_all")),
    ):
        ...
"""
from __future__ import annotations
from typing import Callable

from fastapi import Depends, HTTPException, status

from .auth import get_current_user
from .rbac import has_permission, role_is_at_least, get_effective_role


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_permission(permission: str) -> Callable:
    """Dependency factory: require a specific permission string."""
    async def _check(user: dict = Depends(get_current_user)) -> None:
        role = get_effective_role(user)
        if not has_permission(role, permission):
            raise AuthorizationError(f"Role '{role}' missing permission: {permission}")
    return _check


def require_role_at_least(minimum_role: str) -> Callable:
    """Dependency factory: require role >= minimum in hierarchy."""
    async def _check(user: dict = Depends(get_current_user)) -> None:
        role = get_effective_role(user)
        if not role_is_at_least(role, minimum_role):
            raise AuthorizationError(
                f"Requires at least '{minimum_role}' role (current: '{role}')"
            )
    return _check
