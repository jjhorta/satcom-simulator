#!/usr/bin/env bash
# deploy.sh — Rebuild and restart the constellation simulator stack.
# Also reloads nginx-proxy-manager so it re-resolves container IPs after
# --force-recreate reassigns them.
set -e

cd "$(dirname "$0")"

echo "==> Building images..."
sudo docker compose build api frontend worker

echo "==> Restarting containers..."
sudo docker compose up -d --force-recreate api frontend worker

echo "==> Reloading nginx proxy (flush DNS cache)..."
sudo docker exec nginx-proxy-manager nginx -s reload

echo "==> Done. All containers running:"
sudo docker compose ps
