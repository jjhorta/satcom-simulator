"""
web/backend/app/rate_limiter.py — Per-user rate limiting middleware.

Uses an in-memory sliding window counter per user email (extracted from JWT).
For production (multi-worker), swap the deque for Redis.

RBAC Integration: Rate limits are determined by the user's RBAC role.
The decode_token_from_request() function (in RBAC's auth.py) extracts the
email from the JWT, then we look up the user's role from the DB.

Apply as a FastAPI middleware in main.py.
"""

import time
from collections import defaultdict, deque
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from .auth import decode_token_from_request
from .db import get_user_by_email
from .config import Settings, get_settings

# Rate limits per RBAC role (requests per minute)
RATE_LIMITS: dict[str, int] = {
    "viewer":        10,
    "demo":          20,
    "creator":       60,
    "team_manager":  120,
    "admin":         600,
}

# Paths that bypass rate limiting entirely
BYPASS_PATHS: tuple[str, ...] = (
    "/api/billing/webhook",
    "/api/reports/shared",
    "/api/health",
    "/docs",
    "/openapi.json",
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter per user + role.

    Tracks timestamps of recent requests per user email.
    If a user exceeds their role's rate limit, returns 429.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._windows: dict[str, deque[float]] = defaultdict(deque)
        self._settings: Settings | None = None

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        # Bypass for public/webhook paths
        path = request.url.path
        if any(path.startswith(bp) for bp in BYPASS_PATHS):
            return await call_next(request)

        # Extract user email from JWT
        user_email = decode_token_from_request(request)
        if user_email is None:
            # Unauthenticated — only allow access to very limited endpoints
            # For now, let the auth middleware handle it
            return await call_next(request)

        # Determine role from DB
        if self._settings is None:
            self._settings = get_settings()
        db_user = get_user_by_email(self._settings.outputs_dir, user_email)
        role: str = db_user["role"] if db_user else "viewer"
        limit: int = RATE_LIMITS.get(role, 10)

        # Slide window
        now = time.time()
        window = self._windows[user_email]

        # Remove timestamps older than 60 seconds
        while window and window[0] < now - 60:
            window.popleft()

        if len(window) >= limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded ({limit} requests/minute for {role} role).",
                    "role": role,
                    "limit": limit,
                    "retry_after_seconds": int(60 - (now - window[0])),
                },
            )

        window.append(now)
        return await call_next(request)
