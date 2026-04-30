#!/usr/bin/env bash
# deploy/setup.sh
# Einmaliges Server-Setup für KI-News Briefing auf Hetzner VPS.
# Läuft auf einem frischen Ubuntu 22.04/24.04.
#
# Aufruf: bash deploy/setup.sh

set -euo pipefail

DOMAIN="news.kais.world"
EMAIL="kai@world-direct.at"   # <- für Let's Encrypt Benachrichtigungen anpassen
APP_DIR="/opt/ki-news"
REPO="https://github.com/KaiUnt/ki-news.git"

echo "═══════════════════════════════════════"
echo "  KI-News – Server Setup"
echo "  Domain: $DOMAIN"
echo "═══════════════════════════════════════"

# ── 1. Docker installieren ────────────────────────────────────────────────────
echo ""
echo "▶ 1/6 Docker installieren …"
if ! command -v docker &>/dev/null; then
    apt-get update -q
    apt-get install -y -q ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
      > /etc/apt/sources.list.d/docker.list
    apt-get update -q
    apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
    echo "  ✓ Docker installiert"
else
    echo "  ✓ Docker bereits installiert"
fi

# ── 2. Repo klonen ─────────────────────────────────────────────────────────────
echo ""
echo "▶ 2/6 Repository klonen nach $APP_DIR …"
if [ -d "$APP_DIR" ]; then
    echo "  Verzeichnis existiert – git pull statt clone"
    git -C "$APP_DIR" pull
else
    git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"

# ── 3. .env anlegen ────────────────────────────────────────────────────────────
echo ""
echo "▶ 3/6 .env konfigurieren …"
if [ ! -f "$APP_DIR/ai-briefing-app/.env" ]; then
    echo ""
    echo "  ⚠  ACHTUNG: Keine .env gefunden!"
    echo "  Bitte jetzt $APP_DIR/ai-briefing-app/.env anlegen."
    echo "  Vorlage: $APP_DIR/ai-briefing-app/.env.example"
    echo ""
    echo "  Mindestens folgende Werte setzen:"
    echo "    SUPABASE_URL="
    echo "    SUPABASE_SECRET_KEY="
    echo "    OPENAI_API_KEY="
    echo "    APP_ENV=production"
    echo "    RUN_PASSWORD=<sicheres-passwort>"
    echo ""
    read -p "  Drücke Enter sobald .env angelegt ist …"
fi
echo "  ✓ .env vorhanden"

# ── 4. Zertifikat holen (Certbot, HTTP-Challenge) ─────────────────────────────
echo ""
echo "▶ 4/6 SSL-Zertifikat für $DOMAIN holen …"
echo "  (Port 80 muss erreichbar sein – DNS-Record muss auf diese IP zeigen)"

# Init-Config (nur HTTP) aktivieren
cp "$APP_DIR/nginx/ki-news-init.conf" "$APP_DIR/nginx/ki-news.conf.active"
cp "$APP_DIR/nginx/ki-news-init.conf" /tmp/ki-news-nginx-init.conf

# Docker Compose mit Init-Config starten (nur nginx + certbot volume)
docker compose -f "$APP_DIR/docker-compose.yml" up -d nginx certbot

sleep 3

# Zertifikat beantragen
docker compose -f "$APP_DIR/docker-compose.yml" run --rm certbot \
    certonly --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

echo "  ✓ SSL-Zertifikat erhalten"

# ── 5. Produktions-Nginx-Config aktivieren + App starten ─────────────────────
echo ""
echo "▶ 5/6 App starten …"
# Produktions-Config (HTTP redirect + HTTPS proxy) ist bereits nginx/ki-news.conf
docker compose -f "$APP_DIR/docker-compose.yml" up -d --build

echo "  ✓ App läuft"

# ── 6. Systemd-Timer für Cronjob einrichten ────────────────────────────────────
echo ""
echo "▶ 6/6 Cronjob einrichten (täglich 07:00 Uhr) …"
cp "$APP_DIR/deploy/ki-news-briefing.service" /etc/systemd/system/
cp "$APP_DIR/deploy/ki-news-briefing.timer"   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ki-news-briefing.timer
echo "  ✓ Timer aktiv"

echo ""
echo "═══════════════════════════════════════"
echo "  ✓ Setup abgeschlossen!"
echo "  App:    https://$DOMAIN"
echo "  Status: docker compose -f $APP_DIR/docker-compose.yml ps"
echo "  Logs:   docker logs ki-news-app -f"
echo "═══════════════════════════════════════"
