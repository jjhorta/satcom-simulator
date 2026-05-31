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

    # All self-registrations start as Demo (14-day trial)
    role = "demo"
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


# ── Password reset ──────────────────────────────────────────────────────

import secrets
import smtplib
import ssl
import sqlite3
from email.mime.text import MIMEText

# File-based reset token storage (survives restarts)
import json
from pathlib import Path

_RESET_TOKENS_PATH: Path | None = None

def _get_reset_tokens_path(settings) -> Path:
    global _RESET_TOKENS_PATH
    if _RESET_TOKENS_PATH is None:
        _RESET_TOKENS_PATH = settings.outputs_dir / "reset_tokens.json"
    return _RESET_TOKENS_PATH

def _load_reset_tokens(settings) -> dict:
    path = _get_reset_tokens_path(settings)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except:
            pass
    return {}

def _save_reset_tokens(settings, tokens: dict) -> None:
    path = _get_reset_tokens_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tokens, indent=2))


@router.post("/forgot-password")
async def forgot_password(
    body: dict,
    settings: Settings = Depends(get_settings),
):
    """Send password reset email."""
    email = body.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user = get_user_by_email(settings.outputs_dir, email)
    if not user:
        # Don't reveal whether email exists
        return {"status": "ok", "detail": "If that email is registered, a reset link has been sent."}

    # Generate reset token (valid for 1 hour)
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    tokens = _load_reset_tokens(settings)
    tokens[token] = {"email": email, "expires_at": expires}
    _save_reset_tokens(settings, tokens)

    # Build reset link
    reset_link = f"{settings.app_url or 'https://constellasim.com'}/reset-password?token={token}"

    # Send email
    smtp_host = settings.smtp_host
    smtp_port = settings.smtp_port
    smtp_user = settings.smtp_username
    smtp_pass = settings.smtp_password

    if not smtp_host or not smtp_pass:
        # SMTP not configured — log instead
        print(f"[forgot-password] Reset link for {email}: {reset_link}")
        return {"status": "ok", "detail": "If that email is registered, a reset link has been sent."}

    msg = MIMEText(
        f"""Hello,

We received a request to reset your Constellation Simulator password.

Click the link below to set a new password:
{reset_link}

This link expires in 1 hour.

If you did not request this, you can safely ignore this email.

— Constellation Simulator Team
"""
    )
    msg["Subject"] = "Constellation Simulator — Password Reset"
    msg["From"] = smtp_user
    msg["To"] = email

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=15) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as e:
        print(f"[forgot-password] SMTP error: {e}")
        return {"status": "ok", "detail": "If that email is registered, a reset link has been sent."}

    return {"status": "ok", "detail": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(
    body: dict,
    settings: Settings = Depends(get_settings),
):
    """Reset password using a valid token."""
    token = body.get("token", "").strip()
    new_password = body.get("password", "")

    if not token or not new_password:
        raise HTTPException(status_code=400, detail="Token and password are required")

    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    tokens = _load_reset_tokens(settings)
    info = tokens.get(token)
    if not info:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    expires = datetime.fromisoformat(info["expires_at"])
    if expires < datetime.now(timezone.utc):
        del tokens[token]
        _save_reset_tokens(settings, tokens)
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

    email = info["email"]
    user = get_user_by_email(settings.outputs_dir, email)
    if not user:
        del tokens[token]
        _save_reset_tokens(settings, tokens)
        raise HTTPException(status_code=400, detail="User not found")

    # Update password
    from ..auth import hash_password
    new_hash = hash_password(new_password)
    user_id = user["id"]

    # Update in DB
    conn = sqlite3.connect(str(settings.outputs_dir / "users.db"))
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
    conn.commit()
    conn.close()

    del tokens[token]
    _save_reset_tokens(settings, tokens)
    return {"status": "ok", "detail": "Password updated successfully"}
