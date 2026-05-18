# 🔐 Constellation Simulator — RBAC & User Management

**Target:** Another LLM (Claude) implementing role-based access control and multi-user management.

**Goal:** Replace the single hardcoded admin with a proper RBAC system supporting 5 roles, team organizations, and user registration.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Database Schema](#2-database-schema)
3. [Roles & Permissions Matrix](#3-roles--permissions-matrix)
4. [Authentication Updates](#4-authentication-updates)
5. [Authorization Middleware](#5-authorization-middleware)
6. [User Management API](#6-user-management-api)
7. [Organization / Team System](#7-organization--team-system)
8. [Job Ownership & Scoping](#8-job-ownership--scoping)
9. [Demo User Lifecycle](#9-demo-user-lifecycle)
10. [Shared Reports (Public Access)](#10-shared-reports-public-access)
11. [Frontend Integration](#11-frontend-integration)
12. [Seed Data & First Admin](#12-seed-data--first-admin)
13. [Validation](#13-validation)

---

## 1. Architecture Overview

### File Layout (new + modified)

```
web/backend/app/
├── config.py                  ← MODIFY: keep ADMIN_USERNAME only as bootstrap
├── db.py                      ← NEW (from pricing doc): SQLite user DB
├── rbac.py                    ← NEW: roles, permissions matrix, authorization helpers
├── auth.py                    ← MODIFY: validate against DB, not .env
├── deps.py                    ← NEW: FastAPI dependency injection for permissions
├── api/
│   ├── auth_routes.py         ← MODIFY: add register, /me, role in response
│   ├── admin_routes.py        ← NEW: user management (list, promote, deactivate)
│   ├── jobs_routes.py         ← MODIFY: scope jobs to user/org, filter by role
│   └── reports_routes.py      ← MODIFY: shared reports stay public
├── models.py                  ← MODIFY: add user/org/role models
├── main.py                    ← MODIFY: seed admin on startup

web/frontend/src/
├── types.ts                   ← MODIFY: add User, Role, Org types
├── api/client.ts              ← MODIFY: add admin API calls
├── store/authStore.ts         ← MODIFY: add role, org_id
├── pages/
│   ├── AdminPage.tsx          ← NEW: user management dashboard
│   ├── TeamPage.tsx           ← NEW: invite members, manage team
│   └── DashboardPage.tsx      ← MODIFY: filter jobs by visibility
└── components/
    └── RoleBadge.tsx          ← NEW: role indicator
```

### Data Flow

```
POST /api/auth/register (email, password, org_name)
  → db.create_user() role="creator"
  → db.create_organization()
  → JWT with { sub, role, org_id }

POST /api/auth/login
  → db.authenticate()
  → JWT with { sub, role, org_id }

Every request:
  → deps.get_current_user()  → JWT → DB lookup → (User, Org) tuple
  → deps.require_role("admin") or deps.require_permission("jobs:create")
  → Handler runs

Shared reports:
  GET /api/reports/shared/:token → NO AUTH → existing logic
```

---

## 2. Database Schema

Add to `web/backend/app/db.py` (or create it if it doesn't exist yet).

### Tables

```sql
-- Core user table
CREATE TABLE IF NOT EXISTS users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    email               TEXT    UNIQUE NOT NULL,
    username            TEXT    UNIQUE NOT NULL,
    password_hash       TEXT    NOT NULL,
    role                TEXT    NOT NULL DEFAULT 'creator',
        -- 'admin', 'team_manager', 'creator', 'viewer', 'demo'
    org_id              INTEGER,                              -- NULL for admins (global)
    is_active           INTEGER DEFAULT 1,
    stripe_customer_id  TEXT    UNIQUE,
    subscription_status TEXT    DEFAULT 'inactive',
    jobs_used_this_month INTEGER DEFAULT 0,
    ai_used_this_month  INTEGER DEFAULT 0,
    current_month       TEXT    DEFAULT (strftime('%Y-%m', 'now')),
    demo_expires_at     TEXT,                                 -- NULL unless role='demo'
    demo_jobs_limit     INTEGER DEFAULT 10,
    demo_jobs_used      INTEGER DEFAULT 0,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    last_login_at       TEXT,
    FOREIGN KEY (org_id) REFERENCES organizations(id)
);

-- Organizations (teams)
CREATE TABLE IF NOT EXISTS organizations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    slug            TEXT    UNIQUE NOT NULL,
    owner_id        INTEGER NOT NULL,     -- the team_manager who created it
    max_members     INTEGER DEFAULT 20,
    stripe_customer_id TEXT UNIQUE,
    subscription_tier TEXT DEFAULT 'free',  -- 'free', 'pro', 'enterprise'
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- Invitations (pending)
CREATE TABLE IF NOT EXISTS invitations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id          INTEGER NOT NULL,
    email           TEXT    NOT NULL,
    role            TEXT    NOT NULL DEFAULT 'creator',
    token           TEXT    UNIQUE NOT NULL,
    expires_at      TEXT    NOT NULL,
    accepted_at     TEXT,
    created_by      INTEGER NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (org_id) REFERENCES organizations(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Permission assignments (for future custom roles — optional now)
CREATE TABLE IF NOT EXISTS role_permissions (
    role        TEXT NOT NULL,
    permission  TEXT NOT NULL,
    PRIMARY KEY (role, permission)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(email);
```

### Key Functions

```python
# ── User CRUD ────────────────────────────────────────────────────────────────

def create_user(outputs_dir, email, username, password_hash,
                role='creator', org_id=None, demo_expires_at=None) -> dict:
    ...

def get_user_by_email(outputs_dir, email) -> Optional[dict]:
    ...

def get_user_by_id(outputs_dir, user_id) -> Optional[dict]:
    ...

def authenticate_user(outputs_dir, email, password) -> Optional[dict]:
    """Verify password hash and return user dict. Updates last_login_at."""

def update_user_role(outputs_dir, user_id, new_role) -> bool:
    """Admin-only: change a user's role."""

def deactivate_user(outputs_dir, user_id) -> bool:
    """Soft-delete: set is_active=0."""

def list_users(outputs_dir, org_id=None, role=None, page=1, per_page=50) -> dict:
    """List users with optional filters. Used by admin dashboard."""
    ...

# ── Organization CRUD ────────────────────────────────────────────────────────

def create_organization(outputs_dir, name, owner_id) -> dict:
    ...

def get_organization(outputs_dir, org_id) -> Optional[dict]:
    ...

def get_org_members(outputs_dir, org_id) -> list[dict]:
    ...

# ── Invitation CRUD ─────────────────────────────────────────────────────────

def create_invitation(outputs_dir, org_id, email, role, created_by) -> dict:
    """Generate a token, set expiry to 7 days."""
    ...

def accept_invitation(outputs_dir, token, user_id) -> bool:
    """Link user to org, set role, mark invitation as accepted."""
    ...

# ── Demo lifecycle ──────────────────────────────────────────────────────────

def get_demo_users(outputs_dir) -> list[dict]:
    """Return all active demo users. Used by cleanup scheduler."""

def expire_demo_user(outputs_dir, user_id) -> bool:
    """Set role='viewer' and deactivate. Keeps data for 30 days."""
    ...
```

---

## 3. Roles & Permissions Matrix

### File: `web/backend/app/rbac.py`

```python
"""
web/backend/app/rbac.py — Role definitions, permission matrix, and helpers.
"""

from __future__ import annotations
from typing import Optional

# ── Role hierarchy (higher number = more privileges) ─────────────────────────
ROLE_HIERARCHY = {
    "demo":          0,
    "viewer":        1,
    "creator":       2,
    "team_manager":  3,
    "admin":         4,
}

# ── Permission matrix ────────────────────────────────────────────────────────
# Each permission is a string like "jobs:create", "users:manage"
# The matrix maps role → set of permissions

PERMISSIONS = {
    # ── Admin: god mode ──────────────────────────────────────────────────
    "admin": {
        "users:manage",           # create, promote, deactivate any user
        "users:view_all",         # see all users across orgs
        "orgs:manage",            # create, merge, delete organizations
        "orgs:view_all",          # see all organizations
        "jobs:create",            # create simulations
        "jobs:view_own",          # own jobs
        "jobs:view_team",         # any job in any org
        "jobs:delete_own",        # own jobs
        "jobs:delete_any",        # any job
        "settings:read",          # read system settings (comms, TCO, routes)
        "settings:write",         # modify system settings
        "billing:manage",         # Stripe, plans, invoices
        "billing:view",           # view billing info
        "reports:share",          # create public share tokens
        "reports:view_all",       # any report in any org
        "api:access",             # programmatic API access
        "admin:panel",            # access /admin endpoints
    },

    # ── Team Manager: manages one organization ───────────────────────────
    "team_manager": {
        "users:manage",           # invite/promote/demote within own org
        "users:view_team",        # see members of own org
        "orgs:view_own",          # see own org details
        "jobs:create",
        "jobs:view_own",
        "jobs:view_team",         # see jobs from all org members
        "jobs:delete_own",
        "jobs:delete_team",       # delete any job in own org
        "settings:read",          # read-only system settings
        "billing:view",           # view own org billing
        "reports:share",
        "reports:view_team",      # reports from org members
        "api:access",
    },

    # ── Creator: can create simulations, see own work ───────────────────
    "creator": {
        "jobs:create",
        "jobs:view_own",
        "jobs:delete_own",
        "settings:read",
        "reports:share",
        "api:access",
    },

    # ── Viewer: read-only, can see reports ───────────────────────────────
    "viewer": {
        "jobs:view_own",          # only reports/simulations shared with them
        "reports:view_shared",    # can access shared report tokens
        "settings:read",
        "api:access",             # read-only API
    },

    # ── Demo: like creator but with limits ───────────────────────────────
    "demo": {
        "jobs:create",            # but limited to demo_jobs_limit
        "jobs:view_own",
        "settings:read",
        "reports:share",
        "api:access",             # rate-limited
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission."""
    perms = PERMISSIONS.get(role, set())
    return permission in perms


def require_permission(role: str, permission: str):
    """Raise PermissionError if role lacks permission."""
    if not has_permission(role, permission):
        raise PermissionError(
            f"Role '{role}' does not have permission '{permission}'"
        )


def role_is_at_least(user_role: str, minimum_role: str) -> bool:
    """Check if user_role is >= minimum_role in hierarchy."""
    user_level = ROLE_HIERARCHY.get(user_role, -1)
    min_level = ROLE_HIERARCHY.get(minimum_role, 0)
    return user_level >= min_level


def demo_is_expired(user: dict) -> bool:
    """Check if a demo user's time or job limit is reached."""
    from datetime import datetime, timezone
    if user.get("role") != "demo":
        return False
    # Time check
    expires = user.get("demo_expires_at")
    if expires:
        exp = datetime.fromisoformat(expires)
        if datetime.now(timezone.utc) > exp:
            return True
    # Job count check
    if user.get("demo_jobs_limit", 10) <= user.get("demo_jobs_used", 0):
        return True
    return False


def get_effective_role(user: dict) -> str:
    """Return the actual role, demoting demo if expired."""
    if user.get("role") == "demo" and demo_is_expired(user):
        return "viewer"  # expired demo = viewer
    return user["role"]
```

---

## 4. Authentication Updates

### Modify: `web/backend/app/auth.py`

Replace the existing hardcoded admin authentication with DB-backed auth.

```python
"""
web/backend/app/auth.py — JWT authentication against the user database.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
import bcrypt

from .config import Settings, get_settings
from .db import get_user_by_email, authenticate_user as db_auth

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict, settings: Settings) -> str:
    """Create a JWT with user claims: sub, role, org_id, email."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, settings: Settings) -> Optional[dict]:
    """Decode a JWT without DB lookup. Returns payload or None."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
):
    """FastAPI dependency: validate JWT and return user dict from DB."""
    payload = decode_token(token, settings)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )

    user = get_user_by_email(settings.outputs_dir, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated",
        )

    return user


def decode_token_from_request(request) -> Optional[str]:
    """Extract username/email from JWT in request headers (for middleware)."""
    from starlette.requests import Request
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    settings = get_settings()
    payload = decode_token(token, settings)
    return payload.get("sub") if payload else None
```

### Modify: `web/backend/app/api/auth_routes.py`

```python
from ..db import (
    create_user, get_user_by_email, get_organization, create_organization,
    authenticate_user as db_auth,
)
from ..auth import create_access_token, hash_password
from ..rbac import role_is_at_least
from ..deps import require_role

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(
    body: RegisterRequest,
    settings: Settings = Depends(get_settings),
):
    """Register a new user. Creates a personal org for them.

    Flow:
      1. Check email not taken
      2. Hash password
      3. Create user with role='creator' (no org yet)
      4. Create organization named after user
      5. Set user.org_id = new org
      6. Return JWT

    For demo registrations: role='demo', demo_expires_at = now + 14 days
    """
    existing = get_user_by_email(settings.outputs_dir, body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    password_hash = hash_password(body.password)

    # Default: creator with personal org
    role = body.role or "creator"
    demo_expires = None
    if role == "demo":
        from datetime import datetime, timezone, timedelta
        demo_expires = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()

    user = create_user(
        settings.outputs_dir,
        email=body.email,
        username=body.email.split("@")[0],
        password_hash=password_hash,
        role=role,
        demo_expires_at=demo_expires,
    )

    # Create personal org
    org_name = body.org_name or f"{user['username']}'s Team"
    org = create_organization(settings.outputs_dir, org_name, user["id"])

    # Link user to org
    # (update user's org_id — add this to create_user or do separate update)
    from ..db import _get_db_path
    import sqlite3
    conn = sqlite3.connect(str(_get_db_path(settings.outputs_dir)))
    conn.execute("UPDATE users SET org_id = ? WHERE id = ?", (org["id"], user["id"]))
    conn.commit()
    conn.close()

    # Generate token
    token = create_access_token(
        {"sub": user["email"], "role": role, "org_id": org["id"]},
        settings,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "role": role,
            "org_id": org["id"],
            "org_name": org_name,
        },
    }


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    settings: Settings = Depends(get_settings),
):
    """Login with email/username and password. Returns JWT."""
    user = db_auth(settings.outputs_dir, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    org = None
    if user.get("org_id"):
        org = get_organization(settings.outputs_dir, user["org_id"])

    # Determine effective role (demo may be expired)
    from ..rbac import get_effective_role
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

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "role": effective_role,
            "org_id": user.get("org_id"),
            "org_name": org["name"] if org else None,
        },
    }


@router.get("/me")
async def get_me(
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Return current user profile."""
    org = None
    if user.get("org_id"):
        org = get_organization(settings.outputs_dir, user["org_id"])

    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "role": user["role"],
        "org_id": user.get("org_id"),
        "org_name": org["name"] if org else None,
        "is_active": user.get("is_active", True),
        "created_at": user.get("created_at"),
        "jobs_used": user.get("jobs_used_this_month", 0),
        "demo_expires_at": user.get("demo_expires_at"),
        "demo_jobs_remaining": max(0, user.get("demo_jobs_limit", 0) - user.get("demo_jobs_used", 0)) if user.get("role") == "demo" else None,
    }


# ── Request/Response Models ──────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import Optional


class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8)
    org_name: Optional[str] = None
    role: Optional[str] = "creator"  # or "demo"
```

---

## 5. Authorization Middleware & Dependencies

### File: `web/backend/app/deps.py`

```python
"""
web/backend/app/deps.py — FastAPI dependency injection for authorization.

Usage:
    @router.get("/admin/users")
    async def list_users(
        user: dict = Depends(get_current_user),
        _: None = Depends(require_permission("users:view_all")),
    ):
        ...

    @router.post("/jobs")
    async def create_job(
        user: dict = Depends(get_current_user),
        _: None = Depends(require_role_at_least("creator")),
    ):
        ...
"""

from fastapi import Depends, HTTPException, status
from typing import Callable

from .auth import get_current_user
from .rbac import has_permission, role_is_at_least, get_effective_role


class AuthorizationError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def require_permission(permission: str) -> Callable:
    """Dependency factory: require a specific permission.

    Usage: require_permission("jobs:create")
    """
    async def check(user: dict = Depends(get_current_user)) -> None:
        role = get_effective_role(user)
        if not has_permission(role, permission):
            raise AuthorizationError(
                f"Role '{role}' missing permission: {permission}"
            )
    return check


def require_role_at_least(minimum_role: str) -> Callable:
    """Dependency factory: require role >= minimum in hierarchy.

    Usage: require_role_at_least("creator")
    """
    async def check(user: dict = Depends(get_current_user)) -> None:
        role = get_effective_role(user)
        if not role_is_at_least(role, minimum_role):
            raise AuthorizationError(
                f"Requires at least '{minimum_role}' role (current: '{role}')"
            )
    return check


def require_org_member() -> Callable:
    """Dependency factory: require user to be in an org (not global admin)."""
    async def check(user: dict = Depends(get_current_user)) -> None:
        if not user.get("org_id") and user.get("role") != "admin":
            raise AuthorizationError("User must belong to an organization")
    return check


async def get_current_org(
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Return the user's organization, or None for admins."""
    if not user.get("org_id"):
        return None
    from .db import get_organization
    return get_organization(settings.outputs_dir, user["org_id"])
```

---

## 6. User Management API

### File: `web/backend/app/api/admin_routes.py`

```python
"""
web/backend/app/api/admin_routes.py — Admin-only user and org management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from ..auth import get_current_user
from ..deps import require_permission
from ..config import Settings, get_settings
from ..db import (
    get_user_by_id, get_user_by_email, update_user_role, deactivate_user,
    list_users, get_organization, get_org_members, list_organizations,
)
from ..rbac import role_is_at_least

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def admin_list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    role: str = Query(None),
    org_id: int = Query(None),
    search: str = Query(None),
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users:view_all")),
    settings: Settings = Depends(get_settings),
):
    """List all users with optional filters."""
    result = list_users(
        settings.outputs_dir,
        role=role,
        org_id=org_id,
        search=search,
        page=page,
        per_page=per_page,
    )
    return result


@router.patch("/users/{user_id}/role")
async def admin_update_role(
    user_id: int,
    body: UpdateRoleRequest,
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users:manage")),
    settings: Settings = Depends(get_settings),
):
    """Change a user's role. Admin can set any role.
    Team Manager can only set roles within own org.
    """
    target = get_user_by_id(settings.outputs_dir, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # Team Manager constraint: only manage own org
    if user["role"] == "team_manager":
        if target.get("org_id") != user.get("org_id"):
            raise HTTPException(status_code=403, detail="Not a member of your team")
        # team_manager cannot create other team_managers or admins
        if body.new_role in ("admin", "team_manager"):
            raise HTTPException(status_code=403, detail="Cannot promote to this role")

    # Cannot change own role (prevent accidental lockout)
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
    deactivate_user(settings.outputs_dir, user_id)
    return {"success": True}


@router.get("/organizations")
async def admin_list_orgs(
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("orgs:view_all")),
    settings: Settings = Depends(get_settings),
):
    """List all organizations."""
    orgs = list_organizations(settings.outputs_dir)
    return orgs


@router.get("/organizations/{org_id}")
async def admin_get_org(
    org_id: int,
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("orgs:view_all")),
    settings: Settings = Depends(get_settings),
):
    """Get org details + member list."""
    org = get_organization(settings.outputs_dir, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    members = get_org_members(settings.outputs_dir, org_id)
    return {**org, "members": members}


# ── Models ──────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field

class UpdateRoleRequest(BaseModel):
    new_role: str = Field(..., pattern=r"^(admin|team_manager|creator|viewer|demo)$")
```

---

## 7. Organization / Team System

### Invitation Flow

```
Team Manager
  → POST /api/orgs/invite { email, role }     (require_permission "users:manage")
  → Creates invitation with 7-day token
  → (Optional: sends email, or returns link for manual sharing)

User clicks invite link
  → GET /api/orgs/accept?token=xxx            (user must be logged in)
  → Validates token, links user to org
  → User's role updated to invited role

If user doesn't exist yet:
  → Show register page with pre-filled org token
  → After register, auto-accept invitation
```

### API Routes (add to `admin_routes.py` or new `org_routes.py`)

```python
@router.post("/orgs/invite")
async def invite_member(
    body: InviteRequest,
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users:manage")),
    settings: Settings = Depends(get_settings),
):
    """Invite a user to your organization."""
    if not user.get("org_id"):
        raise HTTPException(status_code=400, detail="You don't have an organization")

    # Check org member limit
    from ..db import get_org_members
    members = get_org_members(settings.outputs_dir, user["org_id"])
    org = get_organization(settings.outputs_dir, user["org_id"])
    if len(members) >= org["max_members"]:
        raise HTTPException(status_code=400, detail="Organization member limit reached")

    invite = create_invitation(
        settings.outputs_dir,
        org_id=user["org_id"],
        email=body.email,
        role=body.role,
        created_by=user["id"],
    )

    # Return the invitation link
    invite_link = f"{settings.app_url}/accept-invite?token={invite['token']}"
    return {
        "invitation": invite,
        "link": invite_link,
    }


@router.post("/orgs/accept")
async def accept_invite(
    token: str,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Accept an invitation to join an organization."""
    from ..db import get_invitation_by_token
    invite = get_invitation_by_token(settings.outputs_dir, token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    from datetime import datetime, timezone
    exp = datetime.fromisoformat(invite["expires_at"])
    if datetime.now(timezone.utc) > exp:
        raise HTTPException(status_code=400, detail="Invitation has expired")

    if invite.get("accepted_at"):
        raise HTTPException(status_code=400, detail="Invitation already accepted")

    # Link user to org
    import sqlite3
    from ..db import _get_db_path
    conn = sqlite3.connect(str(_get_db_path(settings.outputs_dir)))
    conn.execute(
        "UPDATE users SET org_id = ?, role = ? WHERE id = ?",
        (invite["org_id"], invite["role"], user["id"]),
    )
    conn.execute(
        "UPDATE invitations SET accepted_at = datetime('now') WHERE id = ?",
        (invite["id"],),
    )
    conn.commit()
    conn.close()

    return {"success": True, "org_id": invite["org_id"], "role": invite["role"]}


@router.get("/orgs/members")
async def list_team_members(
    user: dict = Depends(get_current_user),
    _: None = Depends(require_permission("users:view_team")),
    settings: Settings = Depends(get_settings),
):
    """List members of the user's organization."""
    if not user.get("org_id"):
        return {"members": []}
    from ..db import get_org_members
    members = get_org_members(settings.outputs_dir, user["org_id"])
    return {"members": members}
```

### Frontend: TeamPage.tsx

```tsx
// web/frontend/src/pages/TeamPage.tsx
// Shows:
//   - List of team members with roles
//   - Invite form (email + role selector) — team_manager only
//   - Invitation history (pending/accepted)
//   - Member count / limit
```

---

## 8. Job Ownership & Scoping

### Modify: `web/backend/app/api/jobs_routes.py`

Every job must be associated with a `user_id` and `org_id`.

**In `job.json` (the job metadata file), add:**

```json
{
  "job_id": "abc-123",
  "user_id": 42,
  "org_id": 7,
  "user_email": "user@example.com",
  "username": "johndoe",
  "role": "creator",
  ...
}
```

**Set these when creating a job:**

```python
# In submit_job endpoint:
from ..rbac import has_permission, get_effective_role

user = await get_current_user(token, settings)
role = get_effective_role(user)

# Check permission
if not has_permission(role, "jobs:create"):
    raise HTTPException(status_code=403, detail="Your role does not allow creating simulations")

# Check demo limits
if role == "demo":
    remaining = user.get("demo_jobs_limit", 10) - user.get("demo_jobs_used", 0)
    if remaining <= 0:
        raise HTTPException(status_code=429, detail="Demo simulation limit reached")

# Store ownership in job metadata
job_meta = {
    "user_id": user["id"],
    "org_id": user.get("org_id"),
    "user_email": user["email"],
    "username": user.get("username", user["email"]),
    "role": role,
    # ... other fields
}
```

**List jobs — filter by role:**

```python
@router.get("/jobs")
async def list_jobs(
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    role = get_effective_role(user)

    if has_permission(role, "jobs:view_team"):
        # team_manager + admin: see all jobs in org (or all orgs for admin)
        if role == "admin":
            jobs = list_all_jobs(settings.outputs_dir)
        else:
            jobs = list_org_jobs(settings.outputs_dir, user["org_id"])
    elif has_permission(role, "jobs:view_own"):
        # creator/viewer/demo: see only own jobs
        jobs = list_user_jobs(settings.outputs_dir, user["id"])
    else:
        jobs = []

    return jobs
```

**Delete jobs — scoped by role:**

```python
@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    user: dict = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    job = get_job(settings.outputs_dir, job_id)
    if not job:
        raise HTTPException(status_code=404)

    role = get_effective_role(user)

    if has_permission(role, "jobs:delete_any"):
        pass  # admin can delete anything
    elif has_permission(role, "jobs:delete_team"):
        # team_manager: only jobs in own org
        if job.get("org_id") != user.get("org_id"):
            raise HTTPException(status_code=403)
    elif has_permission(role, "jobs:delete_own"):
        # creator: only own jobs
        if job.get("user_id") != user["id"]:
            raise HTTPException(status_code=403)
    else:
        raise HTTPException(status_code=403)

    # Proceed with deletion
    delete_job_from_store(settings.outputs_dir, job_id)
    return {"success": True}
```

---

## 9. Demo User Lifecycle

### Registration

```python
POST /api/auth/register
{
    "email": "demo@example.com",
    "password": "test1234",
    "role": "demo"                ← explicit demo request
}

# Response includes:
{
    "user": {
        "role": "demo",
        "demo_expires_at": "2026-06-01T12:00:00Z",     # now + 14 days
        "demo_jobs_remaining": 10,
        ...
    }
}
```

### Enforcement (in `jobs_routes.py`)

```python
# Before creating a job, check demo limits:
if role == "demo":
    # Check time expiry
    expires = user.get("demo_expires_at")
    if expires:
        from datetime import datetime, timezone
        exp = datetime.fromisoformat(expires)
        if datetime.now(timezone.utc) > exp:
            raise HTTPException(status_code=403, detail="Demo period has expired")

    # Check job limit
    used = user.get("demo_jobs_used", 0)
    limit = user.get("demo_jobs_limit", 10)
    if used >= limit:
        raise HTTPException(status_code=429, detail="Demo simulation limit reached")

# After creating job, increment counter:
# In db.py:
def increment_demo_job_count(outputs_dir, user_id):
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.execute(
        "UPDATE users SET demo_jobs_used = demo_jobs_used + 1 WHERE id = ?",
        (user_id,),
    )
    conn.commit()
    conn.close()
```

### Auto-Expiry Scheduler

In `web/backend/app/cleanup.py` (or a new demo cleanup routine):

```python
def expire_demo_users(outputs_dir: Path):
    """Daily: find expired demo users and convert them to viewer."""
    from .db import get_demo_users  # returns active demo users
    demos = get_demo_users(outputs_dir)
    for d in demos:
        from ..rbac import demo_is_expired
        if demo_is_expired(d):
            update_user_role(outputs_dir, d["id"], "viewer")
            # Optionally: send email "Your demo has expired, upgrade to Pro!"
```

Schedule in `main.py` startup:

```python
# Run daily demo expiry check
queue.enqueue_in(timedelta(hours=24), expire_demo_users, settings.outputs_dir)
```

### Upgrade Path

When a demo user subscribes (via Stripe), their role changes:

```
demo (Stripe webhook: subscription created)
  → update_user_role() to "creator" (or "team_manager" if org plan)
  → demo fields cleared
  → All existing jobs preserved
```

---

## 10. Shared Reports (Public Access)

**No changes needed.** The existing shared report flow already works without authentication:

```
GET /api/reports/shared/:token?password=xxx
  → No JWT required
  → Validates token + password
  → Returns report data + file URLs

GET /api/reports/shared/:token/jobs/:jobId/files/:filename?password=xxx
  → No JWT required
  → Returns file content

GET /api/reports/shared/:token/jobs/:jobId/csv/:filename?password=xxx
  → No JWT required
  → Returns CSV as JSON
```

**Important:** Ensure that `RateLimitMiddleware` (from the pricing doc) **excludes** these paths:

```python
# In rate_limiter.py:
if path.startswith("/api/reports/shared"):
    return await call_next(request)
```

---

## 11. Frontend Integration

### `RoleBadge.tsx`

```tsx
// web/frontend/src/components/RoleBadge.tsx

const ROLE_STYLES = {
  admin:          'bg-purple-600 text-white',
  team_manager:   'bg-indigo-600 text-white',
  creator:        'bg-blue-600 text-white',
  viewer:         'bg-gray-600 text-gray-200',
  demo:           'bg-amber-600 text-white',
}

const ROLE_LABELS = {
  admin:          'Admin',
  team_manager:   'Team Manager',
  creator:        'Creator',
  viewer:         'Viewer',
  demo:           'Demo',
}

export default function RoleBadge({ role, className = '' }: { role: string; className?: string }) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
        ROLE_STYLES[role] || 'bg-gray-700 text-gray-300'
      } ${className}`}
    >
      {ROLE_LABELS[role] || role}
    </span>
  )
}
```

### `AdminPage.tsx`

```tsx
// web/frontend/src/pages/AdminPage.tsx
// Requires role === 'admin'
// Shows:
//   - User list (table: email, username, role, org, status, created)
//   - Role change dropdown per user
//   - Deactivate button
//   - Organization list + member counts
//   - Create promo codes (from pricing doc)
```

### `authStore.tsx` — Add role and org

```ts
interface AuthState {
  token: string | null
  email: string | null
  username: string | null
  role: 'admin' | 'team_manager' | 'creator' | 'viewer' | 'demo'
  orgId: number | null
  orgName: string | null
  // ...

// After login/register, set these from the response:
setUser({ email, username, role, org_id, org_name }) {
  set({
    email,
    username,
    role,
    orgId: org_id,
    orgName: org_name,
  })
}
```

### Dashboard — Filter by role

- **Admin**: sees all jobs from all orgs (maybe a filter dropdown)
- **Team Manager**: sees all jobs from own org
- **Creator / Demo**: sees only own jobs
- **Viewer**: sees only jobs assigned or shared with them

```tsx
// In DashboardPage.tsx:
const { role, orgId } = useAuthStore()

// When fetching jobs:
const endpoint = role === 'admin'     ? '/api/jobs?scope=all'
               : role === 'team_manager' ? `/api/jobs?org_id=${orgId}`
               : '/api/jobs?scope=own'
```

### Navigation — Show/hide links by role

```tsx
// In the sidebar/header:
{role === 'admin' && <Link to="/admin">Admin Panel</Link>}
{(role === 'admin' || role === 'team_manager') && <Link to="/team">Team</Link>}
{role !== 'viewer' && <Link to="/new-simulation">New Simulation</Link>}
```

---

## 12. Seed Data & First Admin

### `web/backend/app/main.py` — On startup

```python
from .db import init_db, get_user_by_email, create_user, create_organization
from .auth import hash_password

@app.on_event("startup")
async def startup():
    settings = get_settings()
    init_db(settings.outputs_dir)

    # ── Seed admin user if not exists ────────────────────────────────────
    admin = get_user_by_email(settings.outputs_dir, settings.admin_email)
    if not admin:
        password_hash = hash_password(settings.admin_password)
        admin = create_user(
            settings.outputs_dir,
            email=settings.admin_email,
            username=settings.admin_username,
            password_hash=password_hash,
            role="admin",
        )
        print(f"✅ Admin user created: {settings.admin_email}")

    # ── Seed default permissions ────────────────────────────────────────
    # (if role_permissions table is used)
```

### `web/backend/app/config.py` — Add

```python
class Settings(BaseSettings):
    # Bootstrap admin (used on first startup to create the admin user)
    admin_email: str = "admin@constellasim.com"
    admin_username: str = "admin"
    admin_password: str = "CHANGE_ME_ADMIN_PASSWORD"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**IMPORTANT:** After the first startup creates the admin user from `.env`, the DB becomes the source of truth. Subsequent changes to `admin_password` in `.env` do NOT affect the DB password. Admins change their password via `POST /api/auth/change-password`.

---

## 13. Validation

### Test each role's permissions

```bash
# 1. Register as creator
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"creator@test.com","password":"test1234"}'
# → 200, JWT, role="creator"

# 2. Try admin endpoint as creator
curl -H "Authorization: Bearer $CREATOR_TOKEN" \
  http://localhost:8000/api/admin/users
# → 403 Forbidden

# 3. Login as admin
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=admin@constellasim.com&password=admin123'
# → 200, JWT, role="admin"

# 4. List users as admin
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8000/api/admin/users
# → 200, list with roles

# 5. Promote creator to team_manager
curl -X PATCH http://localhost:8000/api/admin/users/2/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_role":"team_manager"}'
# → 200

# 6. Demo user — create jobs until limit
for i in $(seq 1 11); do
  curl -X POST http://localhost:8000/api/jobs \
    -H "Authorization: Bearer $DEMO_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"mode":"heatmap","params":{"sats":12,"planes":3,"altitude":600,"inclination":53}}'
done
# → Job 11 should return 429

# 7. Shared report (no auth)
curl "http://localhost:8000/api/reports/shared/TOKEN123"
# → 200 (public)

# 8. Viewer cannot create jobs
curl -X POST http://localhost:8000/api/jobs \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mode":"heatmap","params":{...}}'
# → 403
```

### Expected DB queries

```sql
-- All users
SELECT id, email, role, org_id, is_active FROM users;

-- Result:
-- 1 | admin@constellasim.com   | admin          | NULL | 1
-- 2 | creator@test.com         | creator        | 1    | 1
-- 3 | viewer@test.com          | viewer         | 1    | 1
-- 4 | demo@test.com            | demo           | 1    | 1

-- All orgs
SELECT id, name, owner_id, max_members FROM organizations;
-- 1 | creator's Team | 2 | 20

-- Pending invitations
SELECT * FROM invitations WHERE accepted_at IS NULL;
```

---

## Implementation Order

| Order | Module | Est. time | Key details |
|-------|--------|-----------|-------------|
| 1 | `db.py` (schema + user CRUD) | 45 min | Tables: users, orgs, invitations, role_permissions |
| 2 | `rbac.py` | 20 min | Matrix, hierarchy, helpers |
| 3 | `auth.py` (DB-backed) | 30 min | Replace hardcoded auth, add register |
| 4 | `auth_routes.py` (register, login, me) | 30 min | Register creates org, login returns role |
| 5 | `deps.py` | 20 min | require_permission, require_role_at_least |
| 6 | `admin_routes.py` | 30 min | User CRUD, org management |
| 7 | `jobs_routes.py` (ownership scoping) | 30 min | Filter by role, demo limits |
| 8 | Team invite flow | 30 min | Invite accept, org membership |
| 9 | Demo lifecycle | 15 min | Limits, expiry, cleanup |
| 10 | Frontend: RoleBadge, AdminPage, TeamPage | 60 min | React components |
| 11 | Frontend: Dashboard filtering | 20 min | Job list scoped by role |
| 12 | Seed admin + startup | 10 min | Bootstrap admin from .env |
| 13 | Test & debug | 45 min | All roles, edge cases |
| **Total** | | **~6.5 hours** | |

---

## Dependencies

- `bcrypt` — already in requirements.txt (used in existing auth)
- `python-jose[cryptography]` — already in requirements.txt
- All other modules: Python stdlib (`sqlite3`, `secrets`, `datetime`)

---

## Potential Pitfalls

1. **JWT expiry vs DB deactivation**: If an admin deactivates a user, their JWT may still be valid for up to 24h (token expiry). The `get_current_user` dependency checks `is_active` on every request, so deactivation takes effect immediately at the API level. Existing tokens will fail on the next API call.

2. **Org-less admins**: Admin users have `org_id = NULL`. All permission checks must handle this gracefully — admin should pass checks even without an org.

3. **Demo to Pro transition**: When a demo user subscribes, the Stripe webhook needs to:
   - Update role from `demo` to `creator` (or `team_manager` depending on plan)
   - Reset `demo_jobs_used` to 0
   - Keep all existing jobs
   
   This requires coordination between the pricing webhook handler and the RBAC system.

4. **Invitation email vs link**: The current implementation returns an invite link directly (no SMTP). For production, integrate with SendGrid / Resend to send the invite via email.

5. **Role change side effects**: Changing a user from `creator` to `viewer` means they lose access to the "New Simulation" button. Their existing jobs remain visible but they cannot create new ones. No data loss.

6. **Shared reports security**: Even though shared reports are public, the share token acts as an implicit authorization. The token is a random 32-char hex string — unguessable in practice. The optional password adds an extra layer.

7. **Backward compatibility**: Existing users in the `.env` file (`ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH`) are migrated on first startup. After that, the `.env` values are no longer used for authentication. Keep the `.env` values as a bootstrap fallback for disaster recovery.
