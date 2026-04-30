#!/usr/bin/env bash
# deploy/update.sh
# Neuste Version aus Git holen und App neu starten.
# Aufruf auf dem Server: bash /opt/ki-news/deploy/update.sh

set -euo pipefail

APP_DIR="/opt/ki-news"

echo "▶ Update: git pull …"
git -C "$APP_DIR" pull

echo "▶ Abhängigkeiten aktualisieren …"
"$APP_DIR/ai-briefing-app/.venv/bin/pip" install --quiet -r "$APP_DIR/ai-briefing-app/requirements.txt"

echo "▶ App neu starten …"
systemctl restart ki-news-app

echo "✓ Update abgeschlossen"
systemctl status ki-news-app --no-pager
