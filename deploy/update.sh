#!/usr/bin/env bash
# deploy/update.sh
# Neuste Version aus Git holen und App neu starten.
# Aufruf auf dem Server: bash /opt/ki-news/deploy/update.sh

set -euo pipefail

APP_DIR="/opt/ki-news"

echo "▶ Update: git pull …"
git -C "$APP_DIR" pull

echo "▶ App neu bauen und starten …"
docker compose -f "$APP_DIR/docker-compose.yml" up -d --build app

echo "✓ Update abgeschlossen"
docker compose -f "$APP_DIR/docker-compose.yml" ps
