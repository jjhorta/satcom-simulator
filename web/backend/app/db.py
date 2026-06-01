"""
web/backend/app/db.py — SQLite-backed user, organization, and invitation storage.

The database lives at {outputs_dir}/users.db so it is persisted on the same
Docker volume as job outputs and settings.
"""
from __future__ import annotations

import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional


# ── Path helpers ──────────────────────────────────────────────────────────────

def _get_db_path(outputs_dir: Path) -> Path:
    return outputs_dir / "users.db"


def _connect(outputs_dir: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(_get_db_path(outputs_dir)))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema initialisation ─────────────────────────────────────────────────────

def init_db(outputs_dir: Path) -> None:
    """Create tables and indexes if they don't exist yet."""
    outputs_dir.mkdir(parents=True, exist_ok=True)
    conn = _connect(outputs_dir)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS organizations (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                name                TEXT    NOT NULL,
                slug                TEXT    UNIQUE NOT NULL,
                owner_id            INTEGER NOT NULL,
                max_members         INTEGER DEFAULT 20,
                stripe_customer_id  TEXT    UNIQUE,
                stripe_subscription_id TEXT,
                subscription_tier   TEXT    DEFAULT 'free',
                subscription_status TEXT    DEFAULT 'inactive',
                subscription_updated_at TEXT,
                created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS users (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                email                   TEXT    UNIQUE NOT NULL,
                username                TEXT    UNIQUE NOT NULL,
                password_hash           TEXT    NOT NULL,
                role                    TEXT    NOT NULL DEFAULT 'creator',
                org_id                  INTEGER,
                is_active               INTEGER DEFAULT 1,
                stripe_customer_id      TEXT    UNIQUE,
                subscription_status     TEXT    DEFAULT 'inactive',
                jobs_used_this_month    INTEGER DEFAULT 0,
                ai_used_this_month      INTEGER DEFAULT 0,
                current_month           TEXT    DEFAULT (strftime('%Y-%m', 'now')),
                demo_expires_at         TEXT,
                demo_jobs_limit         INTEGER DEFAULT 10,
                demo_jobs_used          INTEGER DEFAULT 0,
                google_id               TEXT    UNIQUE,
                twofa_enabled           INTEGER DEFAULT 0,
                created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at              TEXT    NOT NULL DEFAULT (datetime('now')),
                last_login_at           TEXT,
                FOREIGN KEY (org_id) REFERENCES organizations(id)
            );

            CREATE TABLE IF NOT EXISTS invitations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id      INTEGER NOT NULL,
                email       TEXT    NOT NULL,
                role        TEXT    NOT NULL DEFAULT 'creator',
                token       TEXT    UNIQUE NOT NULL,
                expires_at  TEXT    NOT NULL,
                accepted_at TEXT,
                created_by  INTEGER NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (org_id) REFERENCES organizations(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS role_permissions (
                role        TEXT NOT NULL,
                permission  TEXT NOT NULL,
                PRIMARY KEY (role, permission)
            );

            CREATE INDEX IF NOT EXISTS idx_users_email     ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_org       ON users(org_id);
            CREATE INDEX IF NOT EXISTS idx_inv_token       ON invitations(token);
            CREATE INDEX IF NOT EXISTS idx_inv_email       ON invitations(email);

            CREATE TABLE IF NOT EXISTS stripe_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                stripe_event_id TEXT    UNIQUE NOT NULL,
                event_type      TEXT    NOT NULL,
                data            TEXT,
                processed_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS org_usage (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id              INTEGER NOT NULL,
                month               TEXT    NOT NULL,
                jobs_used           INTEGER DEFAULT 0,
                ai_analyses_used    INTEGER DEFAULT 0,
                storage_bytes       INTEGER DEFAULT 0,
                FOREIGN KEY (org_id) REFERENCES organizations(id),
                UNIQUE(org_id, month)
            );

            CREATE INDEX IF NOT EXISTS idx_stripe_events_id ON stripe_events(stripe_event_id);
        """)
        conn.commit()
    finally:
        conn.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    return dict(row) if row else {}


def _slugify(name: str) -> str:
    import re
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


# ── User CRUD ─────────────────────────────────────────────────────────────────

def create_user(
    outputs_dir: Path,
    email: str,
    username: str,
    password_hash: str,
    role: str = "creator",
    org_id: Optional[int] = None,
    demo_expires_at: Optional[str] = None,
) -> dict:
    conn = _connect(outputs_dir)
    try:
        cur = conn.execute(
            """INSERT INTO users
               (email, username, password_hash, role, org_id, demo_expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (email, username, password_hash, role, org_id, demo_expires_at),
        )
        conn.commit()
        return _row_to_dict(
            conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        )
    finally:
        conn.close()


def get_user_by_email(outputs_dir: Path, email: str) -> Optional[dict]:
    conn = _connect(outputs_dir)
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(outputs_dir: Path, user_id: int) -> Optional[dict]:
    conn = _connect(outputs_dir)
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def authenticate_user(outputs_dir: Path, email: str, password: str) -> Optional[dict]:
    """Verify password and return user dict; update last_login_at on success."""
    import bcrypt
    user = get_user_by_email(outputs_dir, email)
    if not user:
        return None
    if not user.get("is_active"):
        return None
    try:
        ok = bcrypt.checkpw(password.encode(), user["password_hash"].encode())
    except Exception:
        return None
    if not ok:
        return None
    # Update last_login_at
    conn = _connect(outputs_dir)
    try:
        conn.execute(
            "UPDATE users SET last_login_at = datetime('now') WHERE id = ?",
            (user["id"],),
        )
        conn.commit()
    finally:
        conn.close()
    user["last_login_at"] = datetime.now(timezone.utc).isoformat()
    return user


def update_user(outputs_dir: Path, user_id: int, **kwargs) -> bool:
    """Generic user field updater."""
    if not kwargs:
        return False
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    conn = _connect(outputs_dir)
    try:
        conn.execute(f"UPDATE users SET {fields}, updated_at = datetime('now') WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()
    return True


def update_user_role(outputs_dir: Path, user_id: int, new_role: str) -> bool:
    return update_user(outputs_dir, user_id, role=new_role)


def deactivate_user(outputs_dir: Path, user_id: int) -> bool:
    return update_user(outputs_dir, user_id, is_active=0)


def list_users(
    outputs_dir: Path,
    org_id: Optional[int] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
) -> dict:
    conditions: list[str] = []
    params: list = []
    if org_id is not None:
        conditions.append("org_id = ?")
        params.append(org_id)
    if role:
        conditions.append("role = ?")
        params.append(role)
    if search:
        conditions.append("(email LIKE ? OR username LIKE ?)")
        like = f"%{search}%"
        params += [like, like]
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * per_page
    conn = _connect(outputs_dir)
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM users {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM users {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [per_page, offset],
        ).fetchall()
        users = [_row_to_dict(r) for r in rows]
        # Strip password_hash from output
        for u in users:
            u.pop("password_hash", None)
    finally:
        conn.close()
    return {"total": total, "page": page, "per_page": per_page, "users": users}


# ── Demo lifecycle ─────────────────────────────────────────────────────────────

def get_demo_users(outputs_dir: Path) -> list[dict]:
    conn = _connect(outputs_dir)
    try:
        rows = conn.execute(
            "SELECT * FROM users WHERE role = 'demo' AND is_active = 1"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def increment_demo_job_count(outputs_dir: Path, user_id: int) -> None:
    conn = _connect(outputs_dir)
    try:
        conn.execute(
            "UPDATE users SET demo_jobs_used = demo_jobs_used + 1 WHERE id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()


# ── Organization CRUD ──────────────────────────────────────────────────────────

def create_organization(outputs_dir: Path, name: str, owner_id: int) -> dict:
    slug_base = _slugify(name)
    conn = _connect(outputs_dir)
    try:
        # Ensure unique slug by appending counter if needed
        slug = slug_base
        counter = 1
        while conn.execute("SELECT 1 FROM organizations WHERE slug = ?", (slug,)).fetchone():
            slug = f"{slug_base}-{counter}"
            counter += 1
        cur = conn.execute(
            "INSERT INTO organizations (name, slug, owner_id) VALUES (?, ?, ?)",
            (name, slug, owner_id),
        )
        conn.commit()
        return _row_to_dict(
            conn.execute("SELECT * FROM organizations WHERE id = ?", (cur.lastrowid,)).fetchone()
        )
    finally:
        conn.close()


def get_organization(outputs_dir: Path, org_id: int) -> Optional[dict]:
    conn = _connect(outputs_dir)
    try:
        row = conn.execute(
            "SELECT * FROM organizations WHERE id = ?", (org_id,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def get_org_members(outputs_dir: Path, org_id: int) -> list[dict]:
    conn = _connect(outputs_dir)
    try:
        rows = conn.execute(
            """SELECT id, email, username, role, is_active, created_at, last_login_at
               FROM users WHERE org_id = ? ORDER BY created_at""",
            (org_id,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def list_organizations(outputs_dir: Path) -> list[dict]:
    conn = _connect(outputs_dir)
    try:
        rows = conn.execute(
            "SELECT * FROM organizations ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ── Invitation CRUD ───────────────────────────────────────────────────────────

def create_invitation(
    outputs_dir: Path,
    org_id: int,
    email: str,
    role: str,
    created_by: int,
) -> dict:
    token = secrets.token_hex(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    conn = _connect(outputs_dir)
    try:
        cur = conn.execute(
            """INSERT INTO invitations (org_id, email, role, token, expires_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (org_id, email, role, token, expires_at, created_by),
        )
        conn.commit()
        return _row_to_dict(
            conn.execute("SELECT * FROM invitations WHERE id = ?", (cur.lastrowid,)).fetchone()
        )
    finally:
        conn.close()


def get_invitation_by_token(outputs_dir: Path, token: str) -> Optional[dict]:
    conn = _connect(outputs_dir)
    try:
        row = conn.execute(
            "SELECT * FROM invitations WHERE token = ?", (token,)
        ).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def accept_invitation(outputs_dir: Path, token: str, user_id: int) -> Optional[dict]:
    inv = get_invitation_by_token(outputs_dir, token)
    if not inv:
        return None
    conn = _connect(outputs_dir)
    try:
        conn.execute(
            "UPDATE users SET org_id = ?, role = ? WHERE id = ?",
            (inv["org_id"], inv["role"], user_id),
        )
        conn.execute(
            "UPDATE invitations SET accepted_at = datetime('now') WHERE id = ?",
            (inv["id"],),
        )
        conn.commit()
    finally:
        conn.close()
    return inv


# ── Stripe event helpers ──────────────────────────────────────────────────

def mark_stripe_event(outputs_dir: Path, event_id: str, event_type: str, data: str = "") -> bool:
    """Idempotent Stripe event processing. Returns True if new, False if duplicate."""
    conn = _connect(outputs_dir)
    try:
        conn.execute(
            "INSERT INTO stripe_events (stripe_event_id, event_type, data) VALUES (?, ?, ?)",
            (event_id, event_type, data),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# ── Org usage helpers ─────────────────────────────────────────────────────

def increment_org_job_count(outputs_dir: Path, org_id: int) -> None:
    """Increment the monthly job counter for an organization."""
    conn = _connect(outputs_dir)
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    conn.execute(
        """INSERT INTO org_usage (org_id, month, jobs_used)
           VALUES (?, ?, 1)
           ON CONFLICT(org_id, month) DO UPDATE SET
               jobs_used = jobs_used + 1""",
        (org_id, month),
    )
    conn.commit()
    conn.close()


def get_org_job_count(outputs_dir: Path, org_id: int) -> int:
    """Get current month's job count for an organization."""
    conn = _connect(outputs_dir)
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    row = conn.execute(
        "SELECT jobs_used FROM org_usage WHERE org_id = ? AND month = ?",
        (org_id, month),
    ).fetchone()
    conn.close()
    return row[0] if row else 0
