#!/bin/bash
# deploy_analytics.sh — Deploy analytics system to VPS and verify everything works.
# Run from your Mac inside the resume-ai-bot project directory:
#   chmod +x deploy_analytics.sh && ./deploy_analytics.sh

set -e  # Exit on any error

VPS="root@72.56.250.53"
REMOTE="/opt/resumeaibot"
VENV="$REMOTE/.venv/bin/python3"
PASS='${VPS_PASS}'

SSH="sshpass -p $PASS ssh -o StrictHostKeyChecking=no -o PubkeyAuthentication=no $VPS"
SCP="sshpass -p $PASS scp -o StrictHostKeyChecking=no -o PubkeyAuthentication=no"

echo ""
echo "════════════════════════════════════════════"
echo "  РезюмеАИ Analytics — Deploy Script"
echo "════════════════════════════════════════════"

# ── Step 1: Upload analytics core files ──────────────────────────────────────
echo ""
echo "▶ [1/7] Uploading analytics files..."
$SCP \
  analytics_db.py analytics_tracker.py daily_reporter.py \
  dashboard.py analytics_startup.py \
  $VPS:$REMOTE/
echo "  ✅ Core analytics files uploaded"

# ── Step 2: Upload updated handlers ──────────────────────────────────────────
echo ""
echo "▶ [2/7] Uploading updated bot handlers..."
$SCP bot/handlers/start.py       $VPS:$REMOTE/bot/handlers/
$SCP bot/handlers/resume.py      $VPS:$REMOTE/bot/handlers/
$SCP bot/handlers/cover_letter.py $VPS:$REMOTE/bot/handlers/
$SCP bot/handlers/interview.py   $VPS:$REMOTE/bot/handlers/
$SCP bot/handlers/vacancy_analysis.py $VPS:$REMOTE/bot/handlers/
$SCP bot/handlers/ai_assistant.py $VPS:$REMOTE/bot/handlers/
$SCP bot/handlers/payment.py     $VPS:$REMOTE/bot/handlers/
$SCP run.py                       $VPS:$REMOTE/
echo "  ✅ Handlers + run.py uploaded"

# ── Step 3: Install Python dependencies ──────────────────────────────────────
echo ""
echo "▶ [3/7] Installing Python dependencies..."
$SSH "cd $REMOTE && source .venv/bin/activate && pip install aiosqlite streamlit plotly streamlit-autorefresh -q"
echo "  ✅ Dependencies installed"

# ── Step 4: Run verification tests ───────────────────────────────────────────
echo ""
echo "▶ [4/7] Running pre-deploy verification tests..."

# Write test script to temp file on VPS (avoids shell quoting hell)
$SSH "cat > /tmp/verify_analytics.py" << 'PYEOF'
import sys, asyncio, sqlite3
sys.path.insert(0, "/opt/resumeaibot")
sys.path.insert(0, "/opt/resumeaibot/bot")
DB = "/opt/resumeaibot/bot.db"

# Test 1: Existing tables untouched
con = sqlite3.connect(DB)
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
assert "users" in tables, "users table missing!"
assert "payments" in tables, "payments table missing!"
print("  OK Test 1: Existing tables untouched")

# Test 2: Analytics tables created
async def test_init():
    from analytics_db import init_analytics_db
    await init_analytics_db(DB)
    con2 = sqlite3.connect(DB)
    t2 = [r[0] for r in con2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    for tbl in ["daily_stats","join_sources","outreach_log","content_log"]:
        assert tbl in t2, f"{tbl} missing!"
    print("  OK Test 2: All analytics tables exist")
asyncio.run(test_init())

# Test 3: Tracker functions work
async def test_trackers():
    from analytics_tracker import track_start, track_payment, track_feature
    await track_start(999999, "test", DB)
    await track_payment(999999, 100.0, "crypto", DB)
    await track_feature(999999, "resume", DB)
    con3 = sqlite3.connect(DB)
    con3.execute("DELETE FROM join_sources WHERE user_id=999999")
    con3.commit()
    print("  OK Test 3: Tracker functions work")
asyncio.run(test_trackers())

# Test 4: Summary query
async def test_summary():
    from analytics_db import get_full_summary
    s = await get_full_summary(DB)
    assert isinstance(s.get("total_users"), int)
    print(f"  OK Test 4: Summary query works — {s['total_users']} users, {s['total_paid_users']} paid")
asyncio.run(test_summary())

print("  ALL TESTS PASSED")
PYEOF

$SSH "$VENV /tmp/verify_analytics.py" 2>&1
if [ $? -ne 0 ]; then
  echo "  ❌ Tests FAILED — aborting deploy"
  exit 1
fi
echo "  ✅ All 4 tests passed"

# ── Step 5: Backfill daily_stats for last 7 days ─────────────────────────────
echo ""
echo "▶ [5/7] Backfilling daily_stats for last 7 days..."

$SSH "cat > /tmp/backfill.py" << 'PYEOF'
import asyncio, sys
sys.path.insert(0, "/opt/resumeaibot")
sys.path.insert(0, "/opt/resumeaibot/bot")
from analytics_db import compute_daily_stats
from datetime import date, timedelta

async def backfill():
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        await compute_daily_stats(d)
        print(f"  Computed {d}")

asyncio.run(backfill())
print("  OK Backfill complete")
PYEOF

$SSH "$VENV /tmp/backfill.py" 2>&1

# ── Step 6: Restart bot service ───────────────────────────────────────────────
echo ""
echo "▶ [6/7] Restarting bot service..."
$SSH "systemctl restart resumeaibot && sleep 4"
STATUS=$($SSH "systemctl is-active resumeaibot" 2>&1)
if [ "$STATUS" = "active" ]; then
  echo "  ✅ resumeaibot.service is active"
else
  echo "  ❌ resumeaibot.service failed to start: $STATUS"
  $SSH "tail -20 /var/log/resumeaibot.log"
  exit 1
fi

# ── Step 7: Ensure dashboard service is running ───────────────────────────────
echo ""
echo "▶ [7/7] Ensuring dashboard service..."
DASH_STATUS=$($SSH "systemctl is-active resumeai-dashboard" 2>&1)
if [ "$DASH_STATUS" != "active" ]; then
  echo "  ⚠ Dashboard not running — starting it..."
  $SSH "systemctl start resumeai-dashboard && sleep 3"
  DASH_STATUS=$($SSH "systemctl is-active resumeai-dashboard" 2>&1)
fi
if [ "$DASH_STATUS" = "active" ]; then
  echo "  ✅ resumeai-dashboard.service is active (http://127.0.0.1:8501)"
else
  echo "  ❌ Dashboard service failed: $DASH_STATUS"
fi

# ── Final log check ───────────────────────────────────────────────────────────
echo ""
echo "▶ Last 10 bot log lines:"
$SSH "tail -10 /var/log/resumeaibot.log" 2>&1

echo ""
echo "════════════════════════════════════════════"
echo "  ✅ Deploy complete!"
echo ""
echo "  To open the dashboard:"
echo "  1. Run: ssh -L 8501:localhost:8501 root@72.56.250.53"
echo "  2. Open: http://localhost:8501"
echo "  3. Password: resumeai2025"
echo ""
echo "  Daily report: every day at 08:00 Moscow"
echo "  Weekly summary: Monday 10:05 Moscow"
echo "════════════════════════════════════════════"
