"""
web/backend/app/api/admin_routes.py — Admin & org management endpoints.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_current_user
from ..config import Settings, get_settings
from ..db import (
    accept_invitation,
    create_invitation,
    deactivate_user,
    get_invitation_by_token,
    get_org_members,
    get_organization,
    get_user_by_id,
    list_organizations,
    list_users,
    update_user_role,
    update_user,
)
from ..deps import require_permission
from ..models import InviteRequest, UpdateRoleRequest
from ..rbac import get_effective_role

router = APIRouter(prefix="/api/admin", tags=["admin"])
org_router = APIRouter(prefix="/api/orgs", tags=["orgs"])


# ── User management ───────────────────────────────────────────────────────────

@router.get("/users")
async def admin_list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    role: str = Query(None),
    org_id: int = Query(None),
    search: str = Query(None),
    _: None = Depends(require_permission("users:view_all")),
    settings: Settings = Depends(get_settings),
):
    """List all users with optional filters. Admin only."""
    return list_users(
        settings.outputs_dir,
        role=role,
        org_id=org_id,
        search=search,
        page=page,
        per_page=per_page,
    )


@router.patch("/users/{user_id}/role")
async def admin_update_role(
    user_id: int,
    body: UpdateRoleRequest,
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users:manage")),
    settings: Settings = Depends(get_settings),
):
    """Change a user's role."""
    target = get_user_by_id(settings.outputs_dir, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Team Manager: only manage own org, cannot escalate to admin/team_manager
    if get_effective_role(user) == "team_manager":
        if target.get("org_id") != user.get("org_id"):
            raise HTTPException(status_code=403, detail="Not a member of your team")
        if body.new_role in ("admin", "team_manager"):
            raise HTTPException(status_code=403, detail="Cannot promote to this role")

    if target["id"] == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    update_user_role(settings.outputs_dir, user_id, body.new_role)
    return {"success": True, "user_id": user_id, "new_role": body.new_role}


@router.post("/users/{user_id}/deactivate")
async def admin_deactivate_user(
    user_id: int,
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users:manage")),
    settings: Settings = Depends(get_settings),
):
    """Soft-deactivate a user account."""
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    deactivate_user(settings.outputs_dir, user_id)
    return {"success": True}


@router.post("/users/{user_id}/activate")
async def admin_activate_user(
    user_id: int,
    _: None = Depends(require_permission("users:manage")),
    settings: Settings = Depends(get_settings),
):
    """Re-activate a deactivated user account."""
    update_user(settings.outputs_dir, user_id, is_active=1)
    return {"success": True}


# ── Organization management ───────────────────────────────────────────────────

@router.get("/organizations")
async def admin_list_orgs(
    _: None = Depends(require_permission("orgs:view_all")),
    settings: Settings = Depends(get_settings),
):
    """List all organizations."""
    return list_organizations(settings.outputs_dir)


@router.get("/organizations/{org_id}")
async def admin_get_org(
    org_id: int,
    _: None = Depends(require_permission("orgs:view_all")),
    settings: Settings = Depends(get_settings),
):
    """Get org details + member list."""
    org = get_organization(settings.outputs_dir, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    members = get_org_members(settings.outputs_dir, org_id)
    return {**org, "members": members}


# ── Team / org routes (accessible by team_manager + admin) ───────────────────

@org_router.get("/members")
async def list_team_members(
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users:view_team")),
    settings: Settings = Depends(get_settings),
):
    """List members of the caller's organization."""
    if not user.get("org_id"):
        return {"members": []}
    members = get_org_members(settings.outputs_dir, user["org_id"])
    return {"members": members}


@org_router.post("/invite")
async def invite_member(
    body: InviteRequest,
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users:manage")),
    settings: Settings = Depends(get_settings),
):
    """Invite a user to your organization. Returns invitation token + link."""
    if not user.get("org_id"):
        raise HTTPException(status_code=400, detail="You don't have an organization")

    members = get_org_members(settings.outputs_dir, user["org_id"])
    org = get_organization(settings.outputs_dir, user["org_id"])
    if org and len(members) >= org.get("max_members", 20):
        raise HTTPException(status_code=400, detail="Organization member limit reached")

    inv = create_invitation(
        settings.outputs_dir,
        org_id=user["org_id"],
        email=body.email,
        role=body.role,
        created_by=user["id"],
    )
    invite_link = f"{settings.app_url}/constellation-simulator/accept-invite?token={inv['token']}"
    return {"invitation": inv, "link": invite_link}


@org_router.post("/accept")
async def accept_invite(
    token: str,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Accept an invitation to join an organization."""
    inv = get_invitation_by_token(settings.outputs_dir, token)
    if not inv:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    exp = datetime.fromisoformat(inv["expires_at"])
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > exp:
        raise HTTPException(status_code=400, detail="Invitation has expired")

    if inv.get("accepted_at"):
        raise HTTPException(status_code=400, detail="Invitation already accepted")

    result = accept_invitation(settings.outputs_dir, token, user["id"])
    if not result:
        raise HTTPException(status_code=400, detail="Could not accept invitation")

    return {"success": True, "org_id": inv["org_id"], "role": inv["role"]}
