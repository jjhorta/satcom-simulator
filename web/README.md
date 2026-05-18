# Constellation Simulator — Web UI

A FastAPI + React web frontend for the constellation simulator, with background job queuing via Redis + RQ.

---

## Architecture

```
nginx (80/443)
├── /api/* → FastAPI (uvicorn, port 8000)
│              └── RQ jobs → Redis queue → RQ worker
│                                          └── subprocess: satsim_radio.py
└── /*     → React SPA (Vite build, port 3000)
```

---

## Quick Start

### 1. Prerequisites

- Docker + Docker Compose ≥ 2.20
- The `constellation_simulator/` repo (parent of this `web/` folder)

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

| Variable              | Description                                 |
|-----------------------|---------------------------------------------|
| `JWT_SECRET_KEY`      | `openssl rand -hex 32`                      |
| `ADMIN_USERNAME`      | Login username                              |
| `ADMIN_PASSWORD_HASH` | bcrypt hash — generate with the command below |
| `CORS_ORIGINS`        | Comma-separated allowed origins             |

Generate password hash:
```bash
python3 -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('YOUR_PASSWORD'))"
```

### 3. Build & run

```bash
cd web/
docker compose up --build
```

The app is available at **http://localhost** (port 80).

---

## Development (local, no Docker)

### Backend

```bash
cd web/backend
pip install -r requirements.txt

# Copy .env.example to .env and fill in values
cp ../.env.example ../.env

# Start Redis (Docker one-liner)
docker run -d -p 6379:6379 redis:7-alpine

# Start API
PYTHONPATH=/path/to/constellation_simulator uvicorn app.main:app --reload --port 8000

# Start worker (separate terminal)
PYTHONPATH=/path/to/constellation_simulator \
OUTPUTS_DIR=/tmp/sim-outputs \
SIMULATOR_ROOT=/path/to/constellation_simulator \
rq worker --url redis://localhost:6379 sim_jobs
```

### Frontend

```bash
cd web/frontend
npm install
npm run dev        # → http://localhost:3000  (proxies /api → localhost:8000)
```

---

## HTTPS (production)

1. Add TLS certificates to `web/nginx/certs/` (`fullchain.pem`, `privkey.pem`)
2. Uncomment the HTTPS server block in `web/nginx/nginx.conf`
3. Update `CORS_ORIGINS` in `.env` to your domain

---

## Simulation modes

| Mode    | Output files                              |
|---------|-------------------------------------------|
| heatmap | CSV (interactive Leaflet map) + PNG       |
| sky     | PNG animation / GIF                       |
| orbit   | HTML (Plotly 3D) + GIF + TXT dashboard + TXT TCO |
| track   | PNG / HTML map                            |
| route   | CSV + PNG                                 |

---

## Output storage

All job outputs are stored in the `outputs` Docker volume, mounted at `/app/outputs/{job_id}/`.
Use `docker compose exec api ls /app/outputs` to inspect.

## Notes & Troubleshooting

- Nginx Proxy Manager (used on this host) may return a generic `404 Not Found` if there is no proxy host configured for your domain. If you see `404 Not Found\nnginx/1.27.5` when visiting your DuckDNS domain, check the Proxy Hosts list in the Nginx Proxy Manager admin UI (default credentials may be `admin` / `admin` on first login) and ensure a proxy host exists for your domain that forwards to the appropriate internal container (for example, `web-nginx-1:80` or directly to `frontend:3000`).

- If Docker commands fail with "permission denied while trying to connect to the Docker daemon socket", ensure your user has access to the Docker socket. Either run the command with `sudo` or add your user to the `docker` group with:

```bash
sudo usermod -aG docker $(whoami) && newgrp docker
```

After adding to the `docker` group, log out and log back in for group changes to apply.
