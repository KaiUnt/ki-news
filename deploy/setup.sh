#!/usr/bin/env bash
# deploy/setup.sh
# Einmaliges Server-Setup für KI-News Briefing auf Hetzner VPS.
# Kein Docker – direkt venv + systemd + nginx (gleiche Struktur wie andere Apps).
# Muss als kai mit sudo-Rechten laufen.
#
# Aufruf: bash /opt/ki-news/deploy/setup.sh

set -euo pipefail

DOMAIN="news.kais.world"
EMAIL="kai.unterrainer@gmx.net"
APP_DIR="/opt/ki-news"
APP_PORT="8003"
REPO="https://github.com/KaiUnt/ki-news.git"
SERVICE_USER="kai"

echo "═══════════════════════════════════════"
echo "  KI-News – Server Setup"
echo "  Domain:  $DOMAIN"
echo "  App-Dir: $APP_DIR"
echo "  Port:    $APP_PORT"
echo "═══════════════════════════════════════"

# ── 1. Repo klonen ─────────────────────────────────────────────────────────────
echo ""
echo "▶ 1/6 Repository klonen nach $APP_DIR …"
if [ -d "$APP_DIR" ]; then
    echo "  Verzeichnis existiert – git pull statt clone"
    git -C "$APP_DIR" pull
else
    git clone "$REPO" "$APP_DIR"
    chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_DIR"
fi

# ── 2. Python venv + Abhängigkeiten ────────────────────────────────────────────
echo ""
echo "▶ 2/6 Python venv einrichten …"
cd "$APP_DIR/ai-briefing-app"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
echo "  ✓ venv und Pakete installiert"

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
    read -rp "  Drücke Enter sobald .env angelegt ist …"
fi
echo "  ✓ .env vorhanden"

# ── 4. systemd-Service für uvicorn ────────────────────────────────────────────
echo ""
echo "▶ 4/6 systemd-Service einrichten …"
# Pfad in Service-Datei dynamisch setzen
sed "s|APP_DIR_PLACEHOLDER|$APP_DIR|g; s|SERVICE_USER_PLACEHOLDER|$SERVICE_USER|g; s|APP_PORT_PLACEHOLDER|$APP_PORT|g" \
    "$APP_DIR/deploy/ki-news-app.service.template" \
    > /etc/systemd/system/ki-news-app.service
systemctl daemon-reload
systemctl enable --now ki-news-app.service
echo "  ✓ ki-news-app.service läuft auf Port $APP_PORT"

# ── 5. Nginx + Certbot ────────────────────────────────────────────────────────
echo ""
echo "▶ 5/6 Nginx-Config + SSL-Zertifikat …"

# Certbot installieren falls nötig
if ! command -v certbot &>/dev/null; then
    apt-get install -y -q certbot python3-certbot-nginx
fi

# Nginx-Vhost aktivieren (erst HTTP-only für Certbot)
cat > /etc/nginx/sites-available/ki-news.conf << NGINX
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}
NGINX
ln -sf /etc/nginx/sites-available/ki-news.conf /etc/nginx/sites-enabled/ki-news.conf
nginx -t && systemctl reload nginx

# Zertifikat holen
certbot certonly --webroot --webroot-path=/var/www/html \
    --email "$EMAIL" --agree-tos --no-eff-email -d "$DOMAIN"

# Vollständige HTTPS-Config einrichten
cat > /etc/nginx/sites-available/ki-news.conf << NGINX
server {
    listen 80;
    server_name $DOMAIN;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;

    location / {
        proxy_pass         http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
NGINX
nginx -t && systemctl reload nginx
echo "  ✓ Nginx konfiguriert + SSL aktiv"

# ── 6. Cronjob (systemd-Timer) ────────────────────────────────────────────────
echo ""
echo "▶ 6/6 Täglichen Briefing-Timer einrichten …"
sed "s|APP_DIR_PLACEHOLDER|$APP_DIR|g; s|SERVICE_USER_PLACEHOLDER|$SERVICE_USER|g" \
    "$APP_DIR/deploy/ki-news-briefing.service.template" \
    > /etc/systemd/system/ki-news-briefing.service
cp "$APP_DIR/deploy/ki-news-briefing.timer" /etc/systemd/system/ki-news-briefing.timer
systemctl daemon-reload
systemctl enable --now ki-news-briefing.timer
echo "  ✓ Timer aktiv (täglich 07:00 Uhr)"

echo ""
echo "═══════════════════════════════════════"
echo "  ✓ Setup abgeschlossen!"
echo "  App:    https://$DOMAIN"
echo "  Status: systemctl status ki-news-app"
echo "  Logs:   journalctl -u ki-news-app -f"
echo "═══════════════════════════════════════"
