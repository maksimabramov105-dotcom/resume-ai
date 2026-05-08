#!/usr/bin/env bash
# deploy_all.sh — Authoritative full deploy script for resumeai-bot
#
# Usage: bash deploy_all.sh [--skip-build] [--skip-tests]
#
# Requirements:
#   • SSH key access to root@72.56.250.53 (no password needed)
#   • Node.js ≥18 + npm locally (for Next.js build)
#   • rsync available locally
#
# Architecture refresher:
#   • resumeaibot.service  — Python bot + mini-API on :8000
#   • autoapply.service    — FastAPI autoapply on :8080
#   • nginx serves:
#       /             → landing/index.html  (root)
#       /_next/       → frontend/out/_next/ (compiled JS/CSS)
#       /app /api     → proxy :8080
#

set -euo pipefail

VPS="root@72.56.250.53"
REMOTE="/opt/resumeaibot"
LOCAL="$(cd "$(dirname "$0")" && pwd)"
SKIP_BUILD=0
SKIP_TESTS=0

for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=1 ;;
    --skip-tests) SKIP_TESTS=1 ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────────────────────
step() { echo ""; echo "▶  $*"; }
ok()   { echo "   ✅ $*"; }
warn() { echo "   ⚠️  $*"; }
fail() { echo "   ❌ $*"; exit 1; }

rsync_to() {
  local src="$1" dst="$2"
  shift 2
  rsync -az --checksum --delete \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyc' \
    --exclude='.env' --exclude='*.db' --exclude='*.log' \
    --exclude='*.map' \
    "$@" \
    "$src" "$VPS:$dst"
}

echo ""
echo "══════════════════════════════════════════════════════"
echo "  🚀  Resume AI Bot — Full Deploy"
echo "  VPS : $VPS"
echo "  From: $LOCAL"
echo "══════════════════════════════════════════════════════"

# ── Pre-flight ────────────────────────────────────────────────────────────────
step "Pre-flight: checking SSH connection..."
ssh -o ConnectTimeout=10 "$VPS" "echo 'SSH OK'" || fail "Cannot reach VPS via SSH"
ok "VPS reachable"

# ── Step 0: Build Next.js ─────────────────────────────────────────────────────
if [ "$SKIP_BUILD" -eq 0 ]; then
  step "Step 1: Building Next.js frontend..."
  (cd "$LOCAL/frontend" && npm run build) || fail "Next.js build failed — deploy aborted"
  # Keep landing/index.html in sync with the freshly built version
  cp "$LOCAL/frontend/out/index.html" "$LOCAL/landing/index.html"
  ok "Build complete; landing/index.html updated"
else
  warn "Skipping Next.js build (--skip-build)"
fi

# ── Step 1: Sync frontend/out → VPS ──────────────────────────────────────────
step "Step 2: Syncing frontend/out/ (JS/CSS chunks)..."
ssh "$VPS" "mkdir -p $REMOTE/frontend/out"
rsync_to "$LOCAL/frontend/out/" "$REMOTE/frontend/out/"
ok "frontend/out/ synced"

# ── Step 2: Sync landing → VPS ───────────────────────────────────────────────
step "Step 3: Syncing landing/ (HTML/assets)..."
ssh "$VPS" "mkdir -p $REMOTE/landing"
rsync_to "$LOCAL/landing/" "$REMOTE/landing/"
ok "landing/ synced"

# ── Step 3: Sync bot → VPS ───────────────────────────────────────────────────
step "Step 4: Syncing bot/ (full — all handlers, utils, services)..."
ssh "$VPS" "mkdir -p $REMOTE/bot"
rsync_to "$LOCAL/bot/" "$REMOTE/bot/"
ok "bot/ synced"

# ── Step 4: Sync api → VPS ───────────────────────────────────────────────────
step "Step 5: Syncing api/ (routes, middleware, schemas)..."
ssh "$VPS" "mkdir -p $REMOTE/api"
rsync_to "$LOCAL/api/" "$REMOTE/api/"
ok "api/ synced"

# ── Step 5: Sync autoapply → VPS ─────────────────────────────────────────────
step "Step 6: Syncing autoapply/ ..."
ssh "$VPS" "mkdir -p $REMOTE/autoapply"
rsync_to "$LOCAL/autoapply/" "$REMOTE/autoapply/" --exclude='tests/'
ok "autoapply/ synced"

# ── Step 6: Sync root-level Python files ─────────────────────────────────────
step "Step 7: Syncing root-level files (run.py, analytics, etc.)..."
ROOT_FILES=(
  run.py
  analytics_db.py
  analytics_startup.py
  analytics_tracker.py
  daily_reporter.py
  health_check.py
  maintenance.py
  marketing_cron.py
  self_healer.py
  requirements.txt
)
for f in "${ROOT_FILES[@]}"; do
  if [ -f "$LOCAL/$f" ]; then
    rsync -az --checksum "$LOCAL/$f" "$VPS:$REMOTE/$f"
  fi
done
ok "Root-level files synced"

# ── Step 7: Run autoapply tests on VPS ───────────────────────────────────────
if [ "$SKIP_TESTS" -eq 0 ] && [ -d "$LOCAL/autoapply/tests" ]; then
  step "Step 8: Running autoapply test suite on VPS..."
  ssh "$VPS" "cd $REMOTE && .venv/bin/python -m pytest autoapply/tests/ -q --tb=short 2>&1" \
    && ok "All tests passed" \
    || { warn "Tests failed — deploy continuing (non-fatal for now)"; }
else
  warn "Skipping tests"
fi

# ── Step 8: Restart services ──────────────────────────────────────────────────
step "Step 9: Restarting services..."
ssh "$VPS" "
  systemctl daemon-reload
  systemctl restart resumeaibot
  sleep 5
  systemctl is-active resumeaibot && echo 'resumeaibot: active' || { echo 'resumeaibot: FAILED'; journalctl -u resumeaibot -n 20 --no-pager; exit 1; }
  systemctl restart autoapply
  sleep 3
  systemctl is-active autoapply && echo 'autoapply: active' || echo 'autoapply: FAILED (check logs)'
"
ok "Services restarted"

# ── Step 9: Smoke test ────────────────────────────────────────────────────────
step "Step 10: Running smoke tests..."
LANDING_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://resumeai-bot.ru/)
CHUNK_HASH=$(grep -o 'main-app-[a-f0-9]*' "$LOCAL/landing/index.html" | head -1)
CHUNK_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://resumeai-bot.ru/_next/static/chunks/${CHUNK_HASH}.js")
API_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://resumeai-bot.ru/api/stats)

[ "$LANDING_CODE" = "200" ] && ok "Landing page: 200" || warn "Landing page: $LANDING_CODE"
[ "$CHUNK_CODE"  = "200" ] && ok "JS chunk ($CHUNK_HASH): 200" || warn "JS chunk: $CHUNK_CODE (nginx may be stale — try: nginx -s reload)"
[ "$API_CODE"    = "200" ] && ok "API /stats: 200" || warn "API /stats: $API_CODE"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════════"
echo "  🎉  Deploy complete!"
echo ""
echo "  Landing : https://resumeai-bot.ru"
echo "  Bot     : https://t.me/ResumeAIRobot"
echo "  API docs: https://resumeai-bot.ru/api/docs"
echo "══════════════════════════════════════════════════════"
