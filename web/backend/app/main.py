from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api.auth_routes import router as auth_router
from .api.jobs_routes import router as jobs_router
from .api.options_routes import router as options_router
from .api.settings_routes import router as settings_router
from .api.ai_routes import router as ai_router
from .api.reports_routes import router as reports_router
from .api.admin_routes import router as admin_router, org_router
from .stripe_integration import router as billing_router
from .api.contact_routes import router as contact_router
from .ai_copilot.router import router as carl_router
from .rate_limiter import RateLimitMiddleware

settings = get_settings()

app = FastAPI(
    title="Constellation Simulator API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(options_router)
app.include_router(settings_router)
app.include_router(ai_router)
app.include_router(reports_router)
app.include_router(admin_router)
app.include_router(org_router)
app.include_router(billing_router)
app.include_router(contact_router)
app.include_router(carl_router)


@app.on_event("startup")
async def startup():
    """Initialise DB and seed the bootstrap admin user if not present."""
    from .db import init_db, get_user_by_email, create_user
    from .auth import hash_password

    init_db(settings.outputs_dir)

    admin = get_user_by_email(settings.outputs_dir, settings.admin_email)
    if not admin:
        pw_hash = hash_password(settings.admin_password)
        create_user(
            settings.outputs_dir,
            email=settings.admin_email,
            username=settings.admin_username,
            password_hash=pw_hash,
            role="admin",
        )
        print(f"✅ Admin user created: {settings.admin_email}")
    else:
        print(f"ℹ️  Admin user already exists: {settings.admin_email}")


@app.post("/api/cron/expire-demos")
async def cron_expire_demos():
    """Downgrade expired demo users to viewer. Run daily via cron."""
    from .config import get_settings
    import sqlite3
    settings = get_settings()
    conn = sqlite3.connect(str(settings.outputs_dir / "users.db"))
    cur = conn.execute(
        "UPDATE users SET role='viewer', updated_at=datetime('now') " +
        "WHERE role='demo' AND demo_expires_at IS NOT NULL " +
        "AND demo_expires_at < datetime('now')"
    )
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return {"status": "ok", "expired": affected}


@app.get("/api/health")
async def health():
    return {"status": "ok"}
