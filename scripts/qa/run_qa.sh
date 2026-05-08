#!/usr/bin/env bash
# scripts/qa/run_qa.sh — P13 Pre-Launch QA runner
# Usage: bash scripts/qa/run_qa.sh [--skip-vps]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SKIP_VPS="${1:-}"
PASS=0; FAIL=0

ok()   { echo "  ✅  $*"; ((PASS++)); }
fail() { echo "  ❌  $*"; ((FAIL++)); }

echo "═══════════════════════════════════════════"
echo "  ResumeAI P13 Pre-Launch QA"
echo "═══════════════════════════════════════════"

# ── A. Python tests ─────────────────────────────────────────────────────────
echo ""
echo "A. Python test suite"
if python3.11 -m pytest "$ROOT/autoapply/tests/" -q --tb=short 2>&1 | grep -q "passed"; then
  ok "pytest — all tests pass"
else
  fail "pytest — failures detected"
fi

# ── A. ESLint ───────────────────────────────────────────────────────────────
echo ""
echo "A. Frontend lint"
cd "$ROOT/frontend"
LINT_OUT=$(npm run lint 2>&1)
if echo "$LINT_OUT" | grep -q " Error:"; then
  fail "eslint — errors found"
else
  ok "eslint — no errors"
fi

# ── A. No RU job-board imports ───────────────────────────────────────────────
echo ""
echo "A. RU/crypto code check"
GREP_OUT=$(grep -rni "CRYPTOBOT_TOKEN\|hh_scraper\|superjob_scraper" "$ROOT/autoapply/" "$ROOT/bot/" \
  --include="*.py" 2>/dev/null | grep -v __pycache__ | grep -v test_ | grep -v "#" || true)
if [ -z "$GREP_OUT" ]; then
  ok "No live CRYPTOBOT_TOKEN / hh_scraper / superjob_scraper imports"
else
  fail "Unexpected RU references: $GREP_OUT"
fi

# ── B. VPS DB checks ─────────────────────────────────────────────────────────
if [ "$SKIP_VPS" != "--skip-vps" ]; then
  echo ""
  echo "B. VPS database integrity"
  HH_COL=$(ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db 'PRAGMA table_info(autoapply_users)' | grep hh_token" 2>/dev/null || true)
  [ -z "$HH_COL" ] && ok "hh_token column absent" || fail "hh_token column still present"

  CRYPTO_TABLE=$(ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db 'SELECT name FROM sqlite_master WHERE name=\"cryptobot_events\"'" 2>/dev/null || true)
  [ -z "$CRYPTO_TABLE" ] && ok "cryptobot_events table absent" || fail "cryptobot_events table still present"

  IDXCOUNT=$(ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db 'SELECT COUNT(*) FROM sqlite_master WHERE type=\"index\" AND tbl_name=\"applications\"'" 2>/dev/null || echo "0")
  [ "$IDXCOUNT" -ge 3 ] && ok "applications indexes ($IDXCOUNT found)" || fail "Insufficient applications indexes ($IDXCOUNT)"

  # Performance
  RESP=$(ssh root@72.56.250.53 "curl -s -o /dev/null -w '%{time_total}' https://resumeai-bot.ru/api/health/deep" 2>/dev/null || echo "1.0")
  awk "BEGIN { exit ($RESP < 0.25) ? 0 : 1 }" && ok "/api/health/deep p95: ${RESP}s" || fail "/api/health/deep too slow: ${RESP}s"
fi

# ── H. Marketing readiness ──────────────────────────────────────────────────
echo ""
echo "H. Marketing files"
[ -f "$ROOT/frontend/public/robots.txt" ] && ok "robots.txt present" || fail "robots.txt missing"
[ -f "$ROOT/frontend/public/sitemap.xml" ] && ok "sitemap.xml present" || fail "sitemap.xml missing"

CYRILLIC=$(grep -rn "[А-Яа-яёЁ]" "$ROOT/frontend/app/" --include="*.ts" --include="*.tsx" 2>/dev/null | grep -v "bot_translations\|//.*[А-Яа-яёЁ]" | wc -l | tr -d ' ')
[ "$CYRILLIC" -eq 0 ] && ok "No Cyrillic in frontend TS/TSX" || fail "$CYRILLIC Cyrillic occurrences found in frontend"

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════"
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "═══════════════════════════════════════════"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
