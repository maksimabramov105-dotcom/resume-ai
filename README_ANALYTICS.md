# РезюмеАИ — Analytics System

Real-time analytics, daily Telegram reports, and a Streamlit dashboard —
all running on the existing VPS without any new services or databases.

---

## Section 1 — Installation

SSH into the VPS and install the new Python dependencies:

```bash
cd /opt/resumeaibot
source .venv/bin/activate
pip install aiosqlite streamlit plotly streamlit-autorefresh
```

No other new dependencies are needed. Everything else (sqlite3, asyncio,
aiogram, APScheduler) is already installed.

---

## Section 2 — Integration Checklist

### Step 1 — Copy files to VPS

```bash
# From your Mac (run these from the resume-ai-bot project root):
scp analytics_db.py analytics_tracker.py daily_reporter.py \
    dashboard.py analytics_startup.py \
    root@72.56.250.53:/opt/resumeaibot/
```

### Step 2 — Add startup initialisation to run.py

Open `/opt/resumeaibot/run.py` and add inside `run_bot()`, right after
the `bot = Bot(...)` line:

```python
from analytics_startup import startup_analytics
from daily_reporter import ADMIN_CHAT_ID
await startup_analytics(bot=bot, admin_chat_id=ADMIN_CHAT_ID)
```

### Step 3 — Add track_start() to /start handler

File: `bot/handlers/start.py` — function `cmd_start()`

Add these two lines right after `user = await get_or_create_user(...)`:

```python
from analytics_tracker import track_start, DB_PATH
await track_start(user.telegram_id, args, DB_PATH)
```

Full context after the change:

```python
user = await get_or_create_user(
    telegram_id=message.from_user.id,
    username=message.from_user.username,
    full_name=message.from_user.full_name,
)
# Referral block stays here unchanged ...
await track_start(user.telegram_id, args, DB_PATH)   # ← NEW
await message.answer(START_MESSAGE, reply_markup=main_menu_kb())
```

### Step 4 — Add track_payment() to payment handlers

**4a. Crypto auto-confirmed** — `bot/handlers/payment.py` → `check_crypto()`

After `await update_payment_status(invoice_id, "succeeded")`:

```python
from analytics_tracker import track_payment, DB_PATH
await track_payment(callback.from_user.id, pkg["price_rub"], "crypto", DB_PATH)
```

**4b. Manual receipt — AI auto-approved** — `got_receipt()`, inside the
`if ai_result.verdict == "approve":` block, after
`await update_payment_status_by_id(payment_db_id, "succeeded")`:

```python
from analytics_tracker import track_payment, DB_PATH
_track_method = "revolut" if payment_method == "revolut" else "card"
await track_payment(message.from_user.id, pkg.get("price_rub", 0), _track_method, DB_PATH)
```

**4c. Admin manually approved** — `admin_approve()`, after
`await update_payment_status_by_id(payment_db_id, "succeeded")`:

```python
from analytics_tracker import track_payment, DB_PATH
pkg_info = PRICING.get(package_key, {"price_rub": 0})
await track_payment(telegram_id, pkg_info["price_rub"], "card", DB_PATH)
```

### Step 5 — Add track_feature() to each feature handler

**Resume** — `bot/handlers/resume.py` → `_generate_and_send()`
After `resume_text, tokens = await generate_resume(...)`:
```python
from analytics_tracker import track_feature, DB_PATH
await track_feature(message.from_user.id, "resume", DB_PATH)
```

**Cover Letter** — `bot/handlers/cover_letter.py` → `got_vacancy()`
After `letter_text, tokens = await generate_cover_letter(...)`:
```python
from analytics_tracker import track_feature, DB_PATH
await track_feature(message.from_user.id, "cover_letter", DB_PATH)
```

**Interview** — `bot/handlers/interview.py` → `finish_interview_handler()`
After `final_text, tokens = await finish_interview(...)`:
```python
from analytics_tracker import track_feature, DB_PATH
await track_feature(callback.from_user.id, "interview", DB_PATH)
```

**Vacancy Analysis** — `bot/handlers/vacancy_analysis.py` → `got_vacancy()`
After `analysis_text, tokens = await analyze_vacancy(vacancy)`:
```python
from analytics_tracker import track_feature, DB_PATH
await track_feature(message.from_user.id, "vacancy_analysis", DB_PATH)
```

**AI Assistant** — `bot/handlers/ai_assistant.py` → `handle_assistant_message()`
After `response, tokens = await chat_completion(...)`:
```python
from analytics_tracker import track_feature, DB_PATH
await track_feature(message.from_user.id, "ai_message", DB_PATH)
```

### Step 6 — Add daily report + weekly summary to existing APScheduler

Open `/opt/resumeaibot/run.py`.

Add these imports at the top (after existing imports):

```python
import sys, os
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from daily_reporter import send_daily_report, send_weekly_summary, ADMIN_CHAT_ID
from analytics_db import DB_PATH
```

Then inside `run_bot()`, right after the existing `scheduler.add_job(...)` call:

```python
# Daily report — every day at 08:00 Moscow time (05:00 UTC)
scheduler.add_job(
    lambda: asyncio.create_task(send_daily_report(bot, ADMIN_CHAT_ID, DB_PATH)),
    CronTrigger(hour=5, minute=0),
    id='daily_report',
    replace_existing=True,
)

# Weekly analytics summary — Monday 07:05 UTC (5 min after existing digest)
scheduler.add_job(
    lambda: asyncio.create_task(send_weekly_summary(bot, ADMIN_CHAT_ID, DB_PATH)),
    CronTrigger(day_of_week='mon', hour=7, minute=5),
    id='weekly_summary',
    replace_existing=True,
)
```

### Step 7 — Run the dashboard

```bash
cd /opt/resumeaibot
source .venv/bin/activate
streamlit run dashboard.py --server.port 8501 --server.address 127.0.0.1
```

### Step 8 — (Optional) Run dashboard as a systemd service

See Section 3 below.

---

## Section 3 — Dashboard as systemd service

Create the file `/etc/systemd/system/resumeai-dashboard.service`:

```ini
[Unit]
Description=РезюмеАИ Analytics Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/resumeaibot
ExecStart=/opt/resumeaibot/.venv/bin/streamlit run /opt/resumeaibot/dashboard.py \
          --server.port 8501 \
          --server.address 127.0.0.1 \
          --server.headless true
Restart=always
RestartSec=5
StandardOutput=append:/var/log/resumeai-dashboard.log
StandardError=append:/var/log/resumeai-dashboard.log
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
systemctl daemon-reload
systemctl enable resumeai-dashboard
systemctl start resumeai-dashboard
systemctl status resumeai-dashboard
```

---

## Section 4 — Getting your Telegram chat ID

If you need to confirm your chat ID, message **@userinfobot** on Telegram.
It will reply with your user ID instantly.

Your admin ID is already set in `daily_reporter.py`:
```python
ADMIN_CHAT_ID = 6246429438
```

---

## Section 5 — Security

**Port 8501 must NOT be publicly accessible.**
The dashboard is bound to `127.0.0.1` (localhost only).

Access it from your Mac via SSH tunnel:

```bash
ssh -L 8501:localhost:8501 root@72.56.250.53
```

Then open **http://localhost:8501** in your browser.
The tunnel stays open as long as the terminal window is open.

For one-command convenience, add this to your `~/.ssh/config` on Mac:

```
Host resumeai
    HostName 72.56.250.53
    User root
    LocalForward 8501 localhost:8501
```

Then just run: `ssh resumeai`

---

## Architecture Overview

```
Bot process (systemd: resumeaibot.service)
  └── run.py
       ├── aiogram bot (polling)
       ├── FastAPI server (port 8000)
       ├── APScheduler
       │    ├── weekly digest        Mon 07:00 UTC
       │    ├── daily_report         Every day 05:00 UTC  ← NEW
       │    └── weekly_summary       Mon 07:05 UTC        ← NEW
       └── analytics_startup()      on start             ← NEW

Handlers (existing, one line added to each):
  start.py         → track_start()
  payment.py       → track_payment()
  resume.py        → track_feature("resume")
  cover_letter.py  → track_feature("cover_letter")
  interview.py     → track_feature("interview")
  vacancy_analysis → track_feature("vacancy_analysis")
  ai_assistant.py  → track_feature("ai_message")

Dashboard process (systemd: resumeai-dashboard.service)
  └── streamlit run dashboard.py (port 8501, localhost only)
       ├── Page 1: Overview
       ├── Page 2: Revenue
       ├── Page 3: Referrals
       ├── Page 4: Growth Channels
       └── Page 5: Goal Tracker

Database: /opt/resumeaibot/bot.db (SQLite)
  ├── users                ← existing, read-only
  ├── payments             ← existing, read-only
  ├── generation_logs      ← existing, read-only
  ├── assistant_conversations ← existing, read-only
  ├── daily_stats          ← NEW (created by analytics_startup)
  ├── join_sources         ← NEW
  ├── outreach_log         ← NEW
  └── content_log          ← NEW
```
