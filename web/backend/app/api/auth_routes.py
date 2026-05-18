from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import create_access_token, hash_password, get_current_user
from ..config import Settings, get_settings
from ..db import (
    authenticate_user as db_auth,
    create_user,
    create_organization,
    get_user_by_email,
    get_organization,
    update_user,
)
from ..models import RegisterRequest, TokenResponse, UserOut
from ..rbac import get_effective_role

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _build_token_response(user: dict, org_name: str | None, settings: Settings) -> dict:
    effective_role = get_effective_role(user)
    token = create_access_token(
        {
            "sub": user["email"],
            "role": effective_role,
            "org_id": user.get("org_id"),
            "user_id": user["id"],
        },
        settings,
    )
    demo_remaining = None
    if user.get("role") == "demo":
        demo_remaining = max(
            0,
            (user.get("demo_jobs_limit") or 10) - (user.get("demo_jobs_used") or 0),
        )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "role": effective_role,
            "org_id": user.get("org_id"),
            "org_name": org_name,
            "demo_expires_at": user.get("demo_expires_at"),
            "demo_jobs_remaining": demo_remaining,
        },
    }


@router.post("/register")
async def register(
    body: RegisterRequest,
    settings: Settings = Depends(get_settings),
):
    """Register a new user + personal organization. Returns JWT."""
    if get_user_by_email(settings.outputs_dir, body.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    role = body.role or "creator"
    if role not in ("creator", "demo"):
        # Only creator and demo allowed on self-registration
        role = "creator"

    demo_expires_at = None
    if role == "demo":
        demo_expires_at = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()

    password_hash = hash_password(body.password)
    username = body.email.split("@")[0]

    user = create_user(
        settings.outputs_dir,
        email=body.email,
        username=username,
        password_hash=password_hash,
        role=role,
        demo_expires_at=demo_expires_at,
    )

    org_name = body.org_name or f"{username}'s Team"
    org = create_organization(settings.outputs_dir, org_name, user["id"])

    # Link user to org
    update_user(settings.outputs_dir, user["id"], org_id=org["id"])
    user["org_id"] = org["id"]

    return _build_token_response(user, org["name"], settings)


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    settings: Settings = Depends(get_settings),
):
    """Login with email (or legacy username) + password. Returns JWT."""
    # Support both email and username login
    email = form_data.username
    # If the input is not an email (no @), try to find by username first
    if "@" not in email:
        # Try it as email anyway (username === admin case)
        user = None
        # Fall through to db_auth which looks up by email
    else:
        user = None

    user = db_auth(settings.outputs_dir, email, form_data.password)

    # Fallback: if login failed and the credential was the admin bootstrap username,
    # try looking up by admin_email
    if user is None and form_data.username == settings.admin_username:
        user = db_auth(settings.outputs_dir, settings.admin_email, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    org_name = None
    if user.get("org_id"):
        org = get_organization(settings.outputs_dir, user["org_id"])
        if org:
            org_name = org["name"]

    return _build_token_response(user, org_name, settings)


@router.get("/me")
async def get_me(
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Return current user profile."""
    org_name = None
    if user.get("org_id"):
        org = get_organization(settings.outputs_dir, user["org_id"])
        if org:
            org_name = org["name"]

    demo_remaining = None
    if user.get("role") == "demo":
        demo_remaining = max(
            0,
            (user.get("demo_jobs_limit") or 10) - (user.get("demo_jobs_used") or 0),
        )

    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "role": get_effective_role(user),
        "org_id": user.get("org_id"),
        "org_name": org_name,
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at"),
        "last_login_at": user.get("last_login_at"),
        "jobs_used_this_month": user.get("jobs_used_this_month", 0),
        "demo_expires_at": user.get("demo_expires_at"),
        "demo_jobs_remaining": demo_remaining,
    }
