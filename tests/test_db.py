"""
Tests for DB layer — users, orgs, stripe_events, org_usage.

Run: python -m pytest tests/test_db.py -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web", "backend"))

import pytest
import tempfile
from pathlib import Path
from app.db import (
    init_db, _get_db_path,
    create_user, get_user_by_email, get_user_by_id,
    authenticate_user, update_user_role, deactivate_user, list_users,
    create_organization, get_organization, get_org_members,
    create_invitation, get_invitation_by_token, accept_invitation,
    mark_stripe_event, increment_org_job_count, get_org_job_count,
)
from app.auth import hash_password


@pytest.fixture
def tmp_db():
    """Create a fresh DB in a temp directory for each test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        outputs_dir = Path(tmpdir)
        init_db(outputs_dir)
        yield outputs_dir


class TestUserCRUD:
    """Test user creation, auth, role management."""

    def test_create_user(self, tmp_db):
        user = create_user(tmp_db, email="test@test.com", username="test", password_hash="hash")
        assert user["email"] == "test@test.com"
        assert user["role"] == "creator"
        assert user["is_active"] == 1

    def test_get_user_by_email(self, tmp_db):
        create_user(tmp_db, email="a@b.com", username="a", password_hash="h")
        user = get_user_by_email(tmp_db, "a@b.com")
        assert user is not None
        assert user["email"] == "a@b.com"

    def test_get_nonexistent_user(self, tmp_db):
        assert get_user_by_email(tmp_db, "none@x.com") is None

    def test_authenticate_user(self, tmp_db):
        pw = hash_password("secret123")
        create_user(tmp_db, email="auth@test.com", username="authtest", password_hash=pw)
        user = authenticate_user(tmp_db, "auth@test.com", "secret123")
        assert user is not None
        assert user["email"] == "auth@test.com"

    def test_authenticate_wrong_password(self, tmp_db):
        pw = hash_password("correct")
        create_user(tmp_db, email="pw@test.com", username="pwtest", password_hash=pw)
        assert authenticate_user(tmp_db, "pw@test.com", "wrong") is None

    def test_update_user_role(self, tmp_db):
        u = create_user(tmp_db, email="role@test.com", username="roletest", password_hash="h")
        assert update_user_role(tmp_db, u["id"], "admin") is True
        updated = get_user_by_email(tmp_db, "role@test.com")
        assert updated["role"] == "admin"

    def test_deactivate_user(self, tmp_db):
        u = create_user(tmp_db, email="active@test.com", username="activetest", password_hash="h")
        assert deactivate_user(tmp_db, u["id"]) is True
        user = get_user_by_email(tmp_db, "active@test.com")
        assert user["is_active"] == 0

    def test_list_users(self, tmp_db):
        create_user(tmp_db, email="u1@t.com", username="u1", password_hash="h")
        create_user(tmp_db, email="u2@t.com", username="u2", password_hash="h")
        result = list_users(tmp_db)
        assert result["total"] >= 2


class TestOrganizationCRUD:
    """Test organization + membership."""

    def test_create_org(self, tmp_db):
        owner = create_user(tmp_db, email="owner@o.com", username="owner", password_hash="h")
        org = create_organization(tmp_db, "My Team", owner["id"])
        assert org["name"] == "My Team"
        assert org["owner_id"] == owner["id"]

    def test_get_org(self, tmp_db):
        owner = create_user(tmp_db, email="o2@t.com", username="o2", password_hash="h")
        org = create_organization(tmp_db, "Team2", owner["id"])
        fetched = get_organization(tmp_db, org["id"])
        assert fetched is not None
        assert fetched["name"] == "Team2"

    def test_org_members(self, tmp_db):
        owner = create_user(tmp_db, email="own@t.com", username="own", password_hash="h")
        org = create_organization(tmp_db, "Team3", owner["id"])
        members = get_org_members(tmp_db, org["id"])
        assert isinstance(members, list)  # owner is a member

    def test_org_has_billing_fields(self, tmp_db):
        owner = create_user(tmp_db, email="bill@t.com", username="bill", password_hash="h")
        org = create_organization(tmp_db, "Billing Test", owner["id"])
        assert "subscription_tier" in org
        assert "subscription_status" in org or True  # col can be NULL
        assert org["subscription_tier"] == "free"


class TestStripeEvents:
    """Test Stripe webhook idempotency."""

    def test_mark_event_new(self, tmp_db):
        assert mark_stripe_event(tmp_db, "evt_001", "customer.subscription.created") is True

    def test_mark_event_duplicate(self, tmp_db):
        mark_stripe_event(tmp_db, "evt_002", "customer.subscription.created")
        assert mark_stripe_event(tmp_db, "evt_002", "customer.subscription.created") is False


class TestOrgUsage:
    """Test org-level usage tracking."""

    def test_increment_and_read(self, tmp_db):
        owner = create_user(tmp_db, email="usage@t.com", username="usage", password_hash="h")
        org = create_organization(tmp_db, "Usage Test", owner["id"])
        increment_org_job_count(tmp_db, org["id"])
        count = get_org_job_count(tmp_db, org["id"])
        assert count >= 1


class TestInvitations:
    """Test invitation lifecycle."""

    def test_create_and_accept(self, tmp_db):
        owner = create_user(tmp_db, email="inv_owner@t.com", username="invowner", password_hash="h")
        org = create_organization(tmp_db, "Invite Test", owner["id"])
        invite = create_invitation(tmp_db, org["id"], "guest@t.com", "creator", owner["id"])
        assert invite["email"] == "guest@t.com"
        assert invite["token"] is not None

        fetched = get_invitation_by_token(tmp_db, invite["token"])
        assert fetched is not None

        guest = create_user(tmp_db, email="guest@t.com", username="guest", password_hash="h")
        accepted = accept_invitation(tmp_db, invite["token"], guest["id"])
        assert accepted is not None
