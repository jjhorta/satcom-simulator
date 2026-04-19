from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .api.auth_routes import router as auth_router
from .api.jobs_routes import router as jobs_router
from .api.options_routes import router as options_router
from .api.settings_routes import router as settings_router

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

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(options_router)
app.include_router(settings_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
