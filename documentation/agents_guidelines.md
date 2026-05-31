# Constellation Simulator — Agent Guidelines

## Identity & Access
- **Sudo password:** `lusospace`
- **Git signing:** always use `git -c commit.gpgsign=false commit`
- **Active branch:** `code/refactor` (diverged from `main`)
- **Admin login:** `admin@constellasim.com` / see `web/.env` for `ADMIN_PASSWORD` (default `CHANGE_ME_ADMIN_PASSWORD`)
- **End every response with:** `NOS Coding Agent 🤖 - <inspiring phrase>`

---

## Architecture

```
Internet → Nginx Proxy Manager (host, port 80/443, OpenResty)
               ↓ /constellation-simulator/api/* → web-api-1:8000
               ↓ /constellation-simulator/*     → web-frontend-1:3000
```

- **NPM is NOT the Docker nginx** — there is a `web-nginx-1` container but NPM bypasses it and proxies directly to `web-api-1` and `web-frontend-1`
- **CRITICAL:** After `docker compose up --force-recreate`, container IPs change → NPM gets 502. Fix:
  ```bash
  echo 'lusospace' | sudo -S docker exec nginx-proxy-manager nginx -s reload
  ```
- NPM config lives at `/data/compose/2/data/nginx/proxy_host/1.conf` (hortahome.duckdns.org)

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3 + FastAPI + Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt passwords |
| DB | SQLite at `/app/outputs/users.db` (WAL mode, FK on) |
| Job queue | Redis + RQ (`web-worker-1`) |
| Frontend | React + Vite + TanStack Query + Zustand + Tailwind |
| Reverse proxy | Nginx Proxy Manager (host) |
| Containers | Docker Compose at `web/docker-compose.yml` |

---

## Key File Locations

```
web/
  backend/
    app/
      main.py            # FastAPI app + startup hook (seeds admin)
      config.py          # Settings (pydantic-settings, reads .env)
      auth.py            # JWT decode, hash_password, get_current_user → returns dict
      db.py              # SQLite CRUD (users, orgs, invitations)
      rbac.py            # 5 roles: demo<viewer<creator<team_manager<admin
      deps.py            # FastAPI Depends: require_permission, require_role_at_least
      api/
        auth_routes.py   # /api/auth/register, /api/auth/login, /api/auth/me
        admin_routes.py  # /api/admin/users, /api/orgs/*
        jobs_routes.py   # /api/jobs — RBAC gated, ownership scoped
      job_store.py       # Reads job JSON files from outputs_dir
    worker/tasks.py      # RQ job execution
  frontend/src/
    api/client.ts        # Axios; baseURL = BASE_URL/api → /constellation-simulator/api
    store/authStore.ts   # Zustand: token, user, role, orgId (persisted to localStorage)
    types.ts             # UserRole, UserInfo, OrgInfo, JobListItem etc.
    pages/
      LoginPage.tsx      # Email + password form → POST /api/auth/login
      RegisterPage.tsx   # Self-registration
      AdminPage.tsx      # Admin only: user table, role change, org list
      TeamPage.tsx       # team_manager + admin: members + invite link
      DashboardPage.tsx  # Main app: role badge, Admin/Team nav links, demo banner
  .env                   # Secrets (JWT_SECRET_KEY, ADMIN_*, CORS_ORIGINS)
  nginx/nginx.conf       # Docker nginx config (NOT used by NPM — bypassed)
```

---

## RBAC System

- Roles (hierarchy): `demo(0)` < `viewer(1)` < `creator(2)` < `team_manager(3)` < `admin(4)`
- `get_current_user` returns a **`dict`** (full DB row), not a string — all route handlers must use:
  ```python
  user: dict = Depends(get_current_user)
  ```
- Permissions defined in `rbac.py`: `jobs:create`, `jobs:delete_any`, `users:manage`, etc.
- Admin is seeded from `settings.admin_email` / `settings.admin_password` on first startup (runs once)
- To reset admin password: update `users.db` directly or delete it and restart api

---

## Build & Deploy Commands

```bash
# Rebuild specific services (reuses cached apt layer — apt has network flakiness)
echo 'lusospace' | sudo -S docker compose -f web/docker-compose.yml build api worker frontend

# Full no-cache build (slow; retry once if apt fails with exit code 100)
echo 'lusospace' | sudo -S docker compose -f web/docker-compose.yml build --no-cache api worker frontend

# Restart containers
echo 'lusospace' | sudo -S docker compose -f web/docker-compose.yml up -d --force-recreate api worker frontend

# ALWAYS reload NPM after container recreation (fixes 502 Bad Gateway)
echo 'lusospace' | sudo -S docker exec nginx-proxy-manager nginx -s reload

# Check logs
echo 'lusospace' | sudo -S docker logs web-api-1 --tail 30

# Git commit + push
git add -A && git -c commit.gpgsign=false commit -m "feat: ..." && git push
```

---

## Known Gotchas

1. **NPM 502 after container recreate** — reload NPM nginx (see above). NPM caches upstream IPs.

2. **`apt-get` network failures** in `--no-cache` builds — retry once; if persistent, use cached build (omit `--no-cache`) since only Python/TS source changed, not system packages.

3. **Disk space** — 58 GB SD card fills up fast with Docker layers. If builds fail with "no space left on device":
   ```bash
   echo 'lusospace' | sudo -S docker system prune -f
   ```

4. **LoginPage duplicate return block** — a previous edit left a second `return (...)` block after the closing `}`. The file was fixed by truncating to 116 lines. Symptom: `TS1128: Declaration or statement expected` at the last line.

5. **`config.py` duplicate field** — `app_url` was defined twice, causing a Pydantic warning. Keep only one.

6. **`main.py` middleware syntax** — `app.add_middleware(RateLimitMiddleware)` must be a separate statement, not nested inside the CORSMiddleware call:
   ```python
   # CORRECT
   app.add_middleware(CORSMiddleware, allow_origins=..., allow_headers=["*"])
   app.add_middleware(RateLimitMiddleware)
   ```

7. **Frontend `BASE_URL`** is `/constellation-simulator/` in production (set by Vite `base` config). All Axios calls prefix with this automatically — never hardcode the path prefix.

8. **Docker nginx (`web-nginx-1`) is ignored by NPM** — changes to `web/nginx/nginx.conf` have no effect on live traffic. NPM proxies directly to `web-api-1` and `web-frontend-1`.

9. **`password.txt` in repo root** — was created accidentally and deleted. Never commit credentials to the repository.

10. **Frontend built as static production files** — `web-frontend-1` serves `/app/dist/` (not a dev server). Source changes require a rebuild + recreate + NPM reload.
