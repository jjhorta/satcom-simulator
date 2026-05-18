"""
PATCH FILE — Modifications to existing RBAC files
==================================================

Apply these changes AFTER the RBAC implementation is complete and committed.
These patches add the Stripe/billing configuration fields and startup hooks.

Patches:
  1. web/backend/app/config.py     — add Stripe settings fields
  2. web/backend/app/main.py       — add startup init + middleware + cleanup scheduler
  3. web/backend/app/api/jobs_routes.py  — add job quota validation
  4. web/backend/app/api/options_routes.py — filter modes/backends by role
  5. web/backend/worker/tasks.py   — pass tier env var for watermark
"""


# ── PATCH 1: config.py ──────────────────────────────────────────────────────
# Add these fields to the Settings class AFTER the existing RBAC fields:

"""
    # ── Stripe ──────────────────────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_pro_year: str = ""
    stripe_price_ent: str = ""
    stripe_price_ent_year: str = ""
    app_url: str = "http://localhost"
"""


# ── PATCH 2: main.py ────────────────────────────────────────────────────────
# Replace the existing startup() with this expanded version.
# Also add middleware imports.

"""
from .db import init_db, get_user_by_email
from .config import get_settings
from .stripe_integration import router as billing_router
from .rate_limiter import RateLimitMiddleware
from .watermark import should_watermark, apply_watermark


@app.on_event("startup")
async def startup():
    settings = get_settings()
    init_db(settings.outputs_dir)

    # Seed admin from .env if not exists
    admin = get_user_by_email(settings.outputs_dir, settings.admin_email)
    if not admin:
        from .auth import hash_password
        from .db import create_user, create_organization
        pw_hash = hash_password(settings.admin_password)
        admin_user = create_user(
            settings.outputs_dir,
            email=settings.admin_email,
            username=settings.admin_username,
            password_hash=pw_hash,
            role="admin",
        )
        print(f"✅ Admin user created: {settings.admin_email}")


# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(RateLimitMiddleware)


# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(billing_router)
"""


# ── PATCH 3: api/jobs_routes.py ──────────────────────────────────────────────
# In the submit_job endpoint, ADD these checks AFTER you have the user dict
# and BEFORE queueing the job:

"""
from ..tier_config import validate_job_params, get_limits
from ..rbac import has_permission, get_effective_role
from ..db import increment_job_count

@router.post("/jobs")
async def submit_job(body: JobRequest, user: dict = Depends(get_current_user), ...):
    role = get_effective_role(user)

    # 1. Check permission
    if not has_permission(role, "jobs:create"):
        raise HTTPException(status_code=403, detail=f"Role '{role}' does not allow creating simulations.")

    # 2. Check demo limit
    if role == "demo":
        demo_used = user.get("demo_jobs_used", 0)
        demo_limit = user.get("demo_jobs_limit", 10)
        if demo_used >= demo_limit:
            raise HTTPException(status_code=429, detail="Demo simulation limit reached. Upgrade to Pro.")

    # 3. Check monthly job quota
    limits = get_limits(role)
    monthly_limit = limits["jobs_per_month"]
    jobs_used = user.get("jobs_used_this_month", 0)
    if monthly_limit != -1 and jobs_used >= monthly_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly job limit reached ({monthly_limit}/{monthly_limit}). Upgrade or wait.",
        )

    # 4. Validate params against role limits
    errors = validate_job_params(role, body.params.model_dump())
    if errors:
        raise HTTPException(status_code=403, detail="; ".join(errors))

    # 5. Check concurrent job limit
    from .job_store import list_jobs
    active_jobs = sum(
        1 for j in list_jobs(settings.outputs_dir)
        if j.get("status") in ("queued", "running")
        and (j.get("org_id") == user.get("org_id") or role == "admin")
    )
    if active_jobs >= limits["concurrent_jobs"]:
        raise HTTPException(status_code=429, detail="Concurrent job limit reached.")

    # 6. Increment counter and set ownership metadata
    increment_job_count(settings.outputs_dir, user["email"])
    job_meta = {
        "user_id": user["id"],
        "org_id": user.get("org_id"),
        "user_email": user["email"],
        "username": user.get("username", user["email"]),
        "role": role,
        # ... rest of job params from body ...
    }

    # ... continue with existing queueing logic ...
"""


# ── PATCH 4: api/options_routes.py ──────────────────────────────────────────
# In get_options(), filter by role instead of returning everything:

"""
from ..rbac import get_effective_role
from ..tier_config import get_limits, mode_allowed

@router.get("")
async def get_options(
    app_settings=Depends(get_settings),
    user: dict = Depends(get_current_user),     # ← RBAC returns dict, not str
):
    c = _get_sim_constants()
    role = get_effective_role(user)
    limits = get_limits(role)

    # Filter modes and backends by role
    available_modes = limits["modes"]
    available_backends = limits["backends"]

    return {
        # ... existing fields ...
        "modes": available_modes,
        "backends": available_backends,
        "role": role,
        "limits": {
            "max_sats": limits["max_sats"],
            "jobs_per_month": limits["jobs_per_month"],
            "concurrent_jobs": limits["concurrent_jobs"],
            "heatmap_resolution": limits["heatmap_resolution"],
            "multi_shell": limits["multi_shell"],
            "export_formats": limits["export_formats"],
            "max_jobs_total": limits.get("max_jobs_total", -1),
        },
    }
"""


# ── PATCH 5: worker/tasks.py ────────────────────────────────────────────────
# In the subprocess.run call that executes satsim_radio.py,
# add the tier to the environment. After the job completes,
# run watermark if needed.

"""
import os
from ..app.watermark import should_watermark, apply_watermark

# When building the subprocess env:
env = os.environ.copy()
tier = job_data.get("role", "viewer")   # passed from job metadata
env["CONSTELLATION_SIM_TIER"] = tier

# After subprocess.run completes:
if should_watermark(tier):
    from pathlib import Path
    for f in Path(output_dir).glob("*.png"):
        apply_watermark(str(f))
"""


# ── PATCH 6: web/backend/requirements.txt ───────────────────────────────────
"""
# Add these to requirements.txt:
stripe>=7.0.0
Pillow>=10.0.0
"""


# ── PATCH 7: .env additions ─────────────────────────────────────────────────
"""
# Add these to the .env file on the remote server:
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_PRO=price_xxx
STRIPE_PRICE_PRO_YEAR=price_xxx
STRIPE_PRICE_ENT=price_xxx
STRIPE_PRICE_ENT_YEAR=price_xxx
APP_URL=https://constellation-sim.example.com
"""
