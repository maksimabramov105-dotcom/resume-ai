#!/bin/bash
# deploy_all.sh — Full deploy of AutoApply + landing page
# Run from LOCAL machine: bash deploy_all.sh

set -e

VPS_IP="72.56.250.53"
VPS_USER="root"
PASS='${VPS_PASS}'
VPS_PATH="/opt/resumeaibot"
LOCAL_PATH="$(cd "$(dirname "$0")" && pwd)"

SSH="sshpass -p '$PASS' ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no $VPS_USER@$VPS_IP"
SCP="sshpass -p '$PASS' scp -o StrictHostKeyChecking=no -o PubkeyAuthentication=no"

# ────────────────────────────────────────────────────────────
# Helper functions
# ────────────────────────────────────────────────────────────
step() { echo ""; echo "🔹 $*"; }
ok()   { echo "   ✅ $*"; }
fail() { echo "   ❌ $*"; exit 1; }

run_remote() {
    eval "sshpass -p '$PASS' ssh \
        -o StrictHostKeyChecking=no \
        -o PubkeyAuthentication=no \
        $VPS_USER@$VPS_IP \"$1\""
}

scp_dir() {
    local src="$1"
    local dst="$2"
    eval "sshpass -p '$PASS' scp -r \
        -o StrictHostKeyChecking=no \
        -o PubkeyAuthentication=no \
        '$src' '$VPS_USER@$VPS_IP:$dst'"
}

scp_file() {
    local src="$1"
    local dst="$2"
    eval "sshpass -p '$PASS' scp \
        -o StrictHostKeyChecking=no \
        -o PubkeyAuthentication=no \
        '$src' '$VPS_USER@$VPS_IP:$dst'"
}

# ────────────────────────────────────────────────────────────
# Pre-flight checks
# ────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════"
echo "  🚀 AutoApply Full Deploy"
echo "  VPS:  $VPS_USER@$VPS_IP"
echo "  Path: $VPS_PATH"
echo "  From: $LOCAL_PATH"
echo "══════════════════════════════════════════════════════"

command -v sshpass >/dev/null 2>&1 || fail "sshpass not installed. Run: brew install hudochenkov/sshpass/sshpass (Mac) or apt install sshpass (Linux)"

echo ""
echo "🔌 Testing VPS connection..."
run_remote "echo 'connection OK'" || fail "Cannot connect to VPS"
ok "VPS reachable"

# ────────────────────────────────────────────────────────────
# Step 1: Upload landing files
# ────────────────────────────────────────────────────────────
step "Step 1/14: Uploading landing page files..."
if [ -d "$LOCAL_PATH/landing" ]; then
    run_remote "mkdir -p $VPS_PATH/landing"
    scp_dir "$LOCAL_PATH/landing/." "$VPS_PATH/landing/"
    ok "landing/ uploaded"
else
    echo "   ⚠️  No landing/ directory found — skipping"
fi

# ────────────────────────────────────────────────────────────
# Step 2: Upload autoapply package
# ────────────────────────────────────────────────────────────
step "Step 2/14: Uploading autoapply package..."
if [ -d "$LOCAL_PATH/autoapply" ]; then
    run_remote "mkdir -p $VPS_PATH/autoapply"
    scp_dir "$LOCAL_PATH/autoapply/." "$VPS_PATH/autoapply/"
    ok "autoapply/ uploaded"
else
    fail "autoapply/ directory not found"
fi

# ────────────────────────────────────────────────────────────
# Step 3: Upload scrapers
# ────────────────────────────────────────────────────────────
step "Step 3/14: Uploading scrapers..."
if [ -d "$LOCAL_PATH/scrapers" ]; then
    run_remote "mkdir -p $VPS_PATH/scrapers"
    scp_dir "$LOCAL_PATH/scrapers/." "$VPS_PATH/scrapers/"
    ok "scrapers/ uploaded"
else
    echo "   ⚠️  No scrapers/ directory found — skipping"
fi

# ────────────────────────────────────────────────────────────
# Step 4: Upload SEO tools
# ────────────────────────────────────────────────────────────
step "Step 4/14: Uploading SEO tools..."
if [ -d "$LOCAL_PATH/seo" ]; then
    run_remote "mkdir -p $VPS_PATH/seo"
    scp_dir "$LOCAL_PATH/seo/." "$VPS_PATH/seo/"
    ok "seo/ uploaded"
else
    echo "   ⚠️  No seo/ directory found — skipping"
fi

# ────────────────────────────────────────────────────────────
# Step 5: Upload utility scripts and service files
# ────────────────────────────────────────────────────────────
step "Step 5/14: Uploading utility scripts and service files..."

for f in health_check.py bug_report.py; do
    if [ -f "$LOCAL_PATH/$f" ]; then
        scp_file "$LOCAL_PATH/$f" "$VPS_PATH/$f"
        ok "$f uploaded"
    else
        echo "   ⚠️  $f not found — skipping"
    fi
done

for f in autoapply.service autoapply-worker.service health-check.service health-check.timer; do
    if [ -f "$LOCAL_PATH/$f" ]; then
        scp_file "$LOCAL_PATH/$f" "/tmp/$f"
        run_remote "cp /tmp/$f /etc/systemd/system/$f"
        ok "$f copied to /etc/systemd/system/"
    else
        echo "   ⚠️  $f not found — skipping"
    fi
done

# ────────────────────────────────────────────────────────────
# Step 6: Install Python dependencies
# ────────────────────────────────────────────────────────────
step "Step 6/14: Installing Python dependencies in .venv..."
run_remote "
    cd $VPS_PATH
    if [ ! -d .venv ]; then
        python3 -m venv .venv
        echo 'Created new virtual environment'
    fi
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install \
        fastapi \
        uvicorn \
        playwright \
        reportlab \
        aiohttp \
        'python-jose[cryptography]' \
        passlib \
        python-multipart \
        aiosqlite \
        requests \
        beautifulsoup4 \
        httpx \
        aiofiles \
        python-dotenv \
        openai \
        -q
    echo 'pip install complete'
"
ok "Python dependencies installed"

# ────────────────────────────────────────────────────────────
# Step 7: Install Playwright browsers
# ────────────────────────────────────────────────────────────
step "Step 7/14: Installing Playwright Chromium browser..."
run_remote "
    cd $VPS_PATH
    .venv/bin/playwright install chromium --with-deps 2>&1 | tail -5
" || echo "   ⚠️  Playwright install had warnings (may be OK if already installed)"
ok "Playwright browser setup complete"

# ────────────────────────────────────────────────────────────
# Step 8: Create directories
# ────────────────────────────────────────────────────────────
step "Step 8/14: Creating required directories..."
run_remote "
    mkdir -p $VPS_PATH/logs
    mkdir -p /tmp/resumes
    mkdir -p $VPS_PATH/seo/manual_submissions
    mkdir -p $VPS_PATH/seo/backlink_content
    chmod 755 $VPS_PATH/logs
    chmod 777 /tmp/resumes
"
ok "Directories created"

# ────────────────────────────────────────────────────────────
# Step 9: Run tests
# ────────────────────────────────────────────────────────────
step "Step 9/14: Running AutoApply test suite..."
if [ -d "$LOCAL_PATH/tests" ]; then
    scp_dir "$LOCAL_PATH/tests" "$VPS_PATH/"
    ok "tests/ uploaded"
    TEST_RESULT=$(run_remote "
        cd $VPS_PATH
        .venv/bin/python3 tests/test_autoapply.py 2>&1
        echo \"EXIT_CODE:\$?\"
    " 2>&1)
    echo "$TEST_RESULT"
    if echo "$TEST_RESULT" | grep -q "EXIT_CODE:1"; then
        echo ""
        echo "   ❌ Tests failed! Aborting deploy."
        echo "   📋 The existing bot (resumeaibot.service) has NOT been touched."
        echo "   Fix the failing tests and re-run deploy_all.sh"
        exit 1
    fi
    ok "All tests passed"
else
    echo "   ⚠️  No tests/ directory found — skipping tests"
fi

# ────────────────────────────────────────────────────────────
# Step 10: Install and enable systemd services
# ────────────────────────────────────────────────────────────
step "Step 10/14: Configuring systemd services..."
run_remote "
    systemctl daemon-reload

    systemctl enable autoapply.service 2>/dev/null || true
    systemctl enable autoapply-worker.service 2>/dev/null || true
    systemctl enable health-check.timer 2>/dev/null || true

    echo 'systemd services enabled'
"
ok "systemd services enabled"

# ────────────────────────────────────────────────────────────
# Step 11: Open firewall
# ────────────────────────────────────────────────────────────
step "Step 11/14: Configuring firewall..."
run_remote "
    if command -v ufw >/dev/null 2>&1; then
        ufw allow 8080/tcp 2>/dev/null || true
        echo 'ufw: port 8080 allowed'
    else
        echo 'ufw not found — skipping firewall config'
    fi
"
ok "Firewall configured (port 8080)"

# ────────────────────────────────────────────────────────────
# Step 12: Restart services
# ────────────────────────────────────────────────────────────
step "Step 12/14: Starting/restarting services..."
run_remote "
    # Restart existing bot (non-destructive — already running)
    if systemctl is-active resumeaibot >/dev/null 2>&1; then
        systemctl restart resumeaibot
        echo 'resumeaibot restarted'
    else
        echo 'resumeaibot not active — not touching it'
    fi

    # Start new AutoApply services
    systemctl start autoapply.service || true
    systemctl start autoapply-worker.service || true
    systemctl start health-check.timer || true

    sleep 3
    echo ''
    echo 'Service status:'
    systemctl is-active resumeaibot       && echo '  resumeaibot:       active' || echo '  resumeaibot:       INACTIVE'
    systemctl is-active autoapply         && echo '  autoapply:         active' || echo '  autoapply:         INACTIVE'
    systemctl is-active autoapply-worker  && echo '  autoapply-worker:  active' || echo '  autoapply-worker:  INACTIVE'
    systemctl is-active health-check.timer && echo '  health-check.timer: active' || echo '  health-check.timer: INACTIVE'
"
ok "Services started"

# ────────────────────────────────────────────────────────────
# Step 13: Health check
# ────────────────────────────────────────────────────────────
step "Step 13/14: Running health check (waiting 10s for services to stabilize)..."
sleep 10
run_remote "
    cd $VPS_PATH
    .venv/bin/python3 health_check.py 2>&1 || true
" || echo "   ⚠️  Health check reported issues (check logs)"
ok "Health check complete"

# ────────────────────────────────────────────────────────────
# Step 14: Final status report
# ────────────────────────────────────────────────────────────
step "Step 14/14: Final status report"
echo ""
run_remote "
    echo '═══════════════════════════════════════════'
    echo '  DEPLOY COMPLETE — Service Status'
    echo '═══════════════════════════════════════════'

    for svc in resumeaibot autoapply autoapply-worker health-check.timer; do
        status=\$(systemctl is-active \$svc 2>/dev/null || echo 'not-found')
        if [ \"\$status\" = 'active' ]; then
            echo \"  ✅ \$svc: \$status\"
        else
            echo \"  ❌ \$svc: \$status\"
        fi
    done

    echo ''
    echo '  Ports listening:'
    ss -tlnp 2>/dev/null | grep -E ':8080|:8501|:443|:80' | awk '{print \"    \" \$4}' || true

    echo ''
    echo '  Recent log tail (autoapply):'
    tail -5 $VPS_PATH/logs/autoapply.log 2>/dev/null || echo '    (no log yet)'

    echo '═══════════════════════════════════════════'
"

echo ""
echo "══════════════════════════════════════════════════════"
echo "  🎉 AutoApply deploy complete!"
echo ""
echo "  Bot:       https://t.me/topbestworkerbot"
echo "  Web app:   http://$VPS_IP:8080"
echo "  API docs:  http://$VPS_IP:8080/docs"
echo "  Dashboard: http://$VPS_IP:8501"
echo ""
echo "  Logs: $VPS_PATH/logs/"
echo "══════════════════════════════════════════════════════"
