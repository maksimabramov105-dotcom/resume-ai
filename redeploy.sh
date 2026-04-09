#!/bin/bash
# redeploy.sh — Full deploy from scratch on a fresh VPS.
# Run this once after: apt update, Python 3.10+ installed.
#
# Usage:
#   bash redeploy.sh
#
# What it does:
#   1. Installs system deps
#   2. Clones/updates the repo
#   3. Installs Python deps
#   4. Creates backup of existing DBs (if any)
#   5. Restores .env (you must place it at /root/.env.resumeai before running)
#   6. Creates all systemd services
#   7. Starts and enables all services
#   8. Verifies everything is running

set -euo pipefail

APP_DIR="/opt/resumeaibot"
REPO_URL="https://github.com/YOUR_GITHUB_USERNAME/resume-ai-bot.git"  # UPDATE THIS
ENV_SOURCE="/root/.env.resumeai"   # Put your .env here before running
LOG="$APP_DIR/logs/redeploy.log"

echo "=========================================="
echo "  ResumeAI Full Redeploy — $(date)"
echo "=========================================="

# ── 1. System dependencies ──────────────────────────────────────────────────
echo "[1/8] Installing system dependencies…"
apt-get update -q
apt-get install -y -q git python3 python3-pip nginx curl

# ── 2. App directory ────────────────────────────────────────────────────────
echo "[2/8] Setting up app directory…"
mkdir -p "$APP_DIR/logs" "$APP_DIR/backups"

if [ -d "$APP_DIR/.git" ]; then
    echo "  → Pulling latest from git…"
    cd "$APP_DIR" && git pull
else
    echo "  → Cloning repo…"
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# ── 3. Python dependencies ──────────────────────────────────────────────────
echo "[3/8] Installing Python dependencies…"
pip3 install -r requirements.txt --break-system-packages -q
pip3 install -r content_marketing/requirements_content.txt --break-system-packages -q
pip3 install aiohttp aiosqlite python-jose passlib bcrypt reportlab cryptography schedule praw vk_api --break-system-packages -q

# ── 4. Backup existing data ─────────────────────────────────────────────────
echo "[4/8] Backing up existing databases (if any)…"
STAMP=$(date +%Y-%m-%d-%H%M)
for db in bot.db autoapply.db; do
    if [ -f "$APP_DIR/$db" ]; then
        cp "$APP_DIR/$db" "$APP_DIR/backups/${db%.db}_pre_redeploy_$STAMP.db"
        echo "  → Backed up $db"
    fi
done

# ── 5. Environment file ─────────────────────────────────────────────────────
echo "[5/8] Setting up .env…"
if [ -f "$ENV_SOURCE" ]; then
    cp "$ENV_SOURCE" "$APP_DIR/.env"
    echo "  → .env copied from $ENV_SOURCE"
elif [ -f "$APP_DIR/.env" ]; then
    echo "  → Existing .env found, keeping it"
else
    echo "  ⚠️  No .env found! Create $APP_DIR/.env before starting services."
    echo "  Required keys: BOT_TOKEN, ADMIN_ID, OPENROUTER_API_KEY, CRYPTOBOT_TOKEN"
fi

# ── 6. Nginx config ─────────────────────────────────────────────────────────
echo "[6/8] Configuring nginx…"
cp "$APP_DIR/nginx_resumeai.conf" /etc/nginx/sites-available/resumeai
ln -sf /etc/nginx/sites-available/resumeai /etc/nginx/sites-enabled/resumeai
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo "  → nginx configured"

# ── 7. Systemd services ─────────────────────────────────────────────────────
echo "[7/8] Installing systemd services…"

# resumeaibot
cat > /etc/systemd/system/resumeaibot.service << 'EOF'
[Unit]
Description=ResumeAI Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/resumeaibot
EnvironmentFile=/opt/resumeaibot/.env
ExecStart=/usr/bin/python3 /opt/resumeaibot/run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# autoapply
cat > /etc/systemd/system/autoapply.service << 'EOF'
[Unit]
Description=АвтоОтклик Web Service (AutoApply)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/resumeaibot
EnvironmentFile=/opt/resumeaibot/.env
ExecStart=/usr/bin/python3 -m uvicorn autoapply.autoapply_main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# autoapply-worker
cat > /etc/systemd/system/autoapply-worker.service << 'EOF'
[Unit]
Description=АвтоОтклик Background Worker
After=network.target autoapply.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/resumeaibot
EnvironmentFile=/opt/resumeaibot/.env
ExecStart=/usr/bin/python3 /opt/resumeaibot/autoapply/worker.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# monitor
cat > /etc/systemd/system/monitor.service << 'EOF'
[Unit]
Description=ResumeAI Service Monitor
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/resumeaibot
EnvironmentFile=/opt/resumeaibot/.env
ExecStart=/usr/bin/python3 /opt/resumeaibot/monitor.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# content-marketing
cat > /etc/systemd/system/content-marketing.service << 'EOF'
[Unit]
Description=ResumeAI Content Marketing Scheduler
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/resumeaibot
EnvironmentFile=/opt/resumeaibot/.env
ExecStart=/usr/bin/python3 /opt/resumeaibot/content_marketing/scheduler.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
for svc in resumeaibot autoapply autoapply-worker monitor content-marketing; do
    systemctl enable "$svc"
    systemctl restart "$svc"
    sleep 2
    status=$(systemctl is-active "$svc")
    echo "  $svc: $status"
done

# ── 8. Verify ───────────────────────────────────────────────────────────────
echo "[8/8] Verifying…"
sleep 5

ALL_OK=true
for svc in resumeaibot autoapply autoapply-worker monitor; do
    if ! systemctl is-active --quiet "$svc"; then
        echo "  ❌ $svc is NOT running"
        journalctl -u "$svc" -n 10 --no-pager
        ALL_OK=false
    else
        echo "  ✅ $svc is running"
    fi
done

# Check HTTP
if curl -s --max-time 5 http://127.0.0.1:8080/api/health | grep -q '"ok"'; then
    echo "  ✅ AutoApply API responding"
else
    echo "  ❌ AutoApply API not responding"
    ALL_OK=false
fi

echo ""
if [ "$ALL_OK" = true ]; then
    echo "✅ Redeploy complete — all systems operational!"
else
    echo "⚠️  Redeploy done with warnings — check logs above"
fi

echo "Logs: journalctl -u resumeaibot -f"
echo "API:  http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR_IP')/"
