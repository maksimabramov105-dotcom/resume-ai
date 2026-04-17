# AutoApply System — Setup & Operations Guide

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INTERFACES                          │
│  Telegram Bot (@topbestworkerbot)    Web App (port 8080)    │
└───────────────────┬───────────────────────┬─────────────────┘
                    │                       │
         ┌──────────▼──────────┐   ┌────────▼────────┐
         │   aiogram 3 Bot     │   │  FastAPI REST   │
         │   (resumeaibot.     │   │  API :8080      │
         │    service)         │   │  (autoapply.    │
         └──────────┬──────────┘   │   service)      │
                    │              └────────┬────────┘
                    └──────────┬────────────┘
                               │
              ┌────────────────▼─────────────────┐
              │         Background Worker         │
              │     (autoapply-worker.service)    │
              │                                   │
              │  ┌────────────┐ ┌──────────────┐  │
              │  │ hh.ru API  │ │ SuperJob API │  │
              │  └────────────┘ └──────────────┘  │
              │  ┌────────────┐ ┌──────────────┐  │
              │  │  LinkedIn  │ │   Indeed     │  │
              │  │ (Playwright│ │  (scraper)   │  │
              │  └────────────┘ └──────────────┘  │
              └────────────────┬─────────────────┘
                               │
              ┌────────────────▼─────────────────┐
              │        SQLite Databases           │
              │  bot.db          autoapply.db     │
              │  (users, plans)  (vacancies,      │
              │                   applications,   │
              │                   resumes)        │
              └───────────────────────────────────┘
                               │
              ┌────────────────▼─────────────────┐
              │      Health Monitor (timer)       │
              │   health-check.timer → 5 min      │
              │   health_check.py                 │
              │   → alerts admin via Telegram     │
              └───────────────────────────────────┘
```

**VPS:** root@72.56.250.53, path /opt/resumeaibot/

**Key files:**
- `autoapply/autoapply_main.py` — FastAPI app
- `autoapply/worker.py` — background job processor
- `health_check.py` — system monitor (runs every 5 min)
- `bug_report.py` — global error handler + Telegram alerts
- `deploy_all.sh` — one-command deploy from local machine

---

## 2. Prerequisites — API Keys Needed

Before deploying, obtain these credentials and add them to `/opt/resumeaibot/.env`:

### hh.ru API (free)
1. Go to https://dev.hh.ru/
2. Register as an employer/developer
3. Create an OAuth application
4. Get `client_id` and `client_secret`
5. The bot handles per-user OAuth tokens during the `/connect_hh` flow

### SuperJob API (free)
1. Register at https://api.superjob.ru/
2. Create an app in your dashboard
3. Get `client_id`, `client_secret`, and `access_token`
4. Rate limit: 5 req/sec — the scraper respects this

### OpenAI API
1. Go to https://platform.openai.com/api-keys
2. Create a new secret key
3. Recommended model: `gpt-4o-mini` (15x cheaper than gpt-4, sufficient quality)
4. Set spending limit in dashboard to avoid surprises
5. **Minimum budget:** $10/month covers ~500 tailored resume generations

### CryptoBot (for crypto payments)
1. Open @CryptoBot in Telegram
2. Go to Crypto Pay → My Apps → Create App
3. Get your API token
4. Free to use — no monthly fee, CryptoBot takes a small % per transaction

### LinkedIn (own account)
1. Use your own LinkedIn account credentials
2. No paid subscription needed for Easy Apply automation
3. IMPORTANT: Use a dedicated account or be conservative (bot defaults to 10 applications/day on LinkedIn to avoid flags)

### Telegram Bot Token
1. Message @BotFather, create or use existing `@topbestworkerbot`
2. Get the token from BotFather

---

## 3. Environment Variables Reference

Add all of these to `/opt/resumeaibot/.env`:

```env
# ── Core ──────────────────────────────────────────
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_ID=0

# ── Database paths ────────────────────────────────
BOT_DB=/opt/resumeaibot/bot.db
AUTOAPPLY_DB=/opt/resumeaibot/autoapply.db
LOGS_DIR=/opt/resumeaibot/logs

# ── AI ────────────────────────────────────────────
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# ── hh.ru OAuth ───────────────────────────────────
HH_CLIENT_ID=your_hh_client_id
HH_CLIENT_SECRET=your_hh_client_secret
HH_REDIRECT_URI=https://resumeai.bot/hh/callback

# ── SuperJob ──────────────────────────────────────
SUPERJOB_CLIENT_ID=your_sj_client_id
SUPERJOB_CLIENT_SECRET=your_sj_client_secret
SUPERJOB_ACCESS_TOKEN=your_sj_access_token

# ── LinkedIn (optional) ───────────────────────────
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password

# ── Payments ──────────────────────────────────────
CRYPTOBOT_TOKEN=your_cryptobot_token
PAYMENT_PROVIDER_TOKEN=your_telegram_payment_token

# ── AutoApply API ─────────────────────────────────
AUTOAPPLY_API_URL=http://localhost:8080
JWT_SECRET_KEY=generate_a_random_32char_string_here
JWT_ALGORITHM=HS256

# ── Web app ───────────────────────────────────────
WEBAPP_URL=https://resumeai.bot/app
DOMAIN=resumeai.bot
```

**Generate JWT secret:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 4. Local Development Setup

```bash
# 1. Clone / navigate to project
cd ~/resume-ai-bot

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
pip install fastapi uvicorn playwright reportlab aiohttp python-jose passlib \
            python-multipart aiosqlite requests beautifulsoup4 httpx openai

# 4. Install Playwright browser
playwright install chromium

# 5. Copy and fill environment file
cp .env.example .env
# Edit .env with your API keys

# 6. Run tests before any changes
python3 tests/test_autoapply.py

# 7. Start bot locally
python3 run.py

# 8. Start AutoApply API locally (separate terminal)
uvicorn autoapply.autoapply_main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 5. Deploy Instructions

### First-time deploy (from local machine)

```bash
# Ensure sshpass is installed
brew install hudochenkov/sshpass/sshpass  # macOS
# or: apt install sshpass                 # Linux

# Run full deploy
bash deploy_all.sh
```

The script will:
1. Upload all files to VPS
2. Install Python dependencies in `/opt/resumeaibot/.venv`
3. Install Playwright Chromium
4. Run the full test suite (aborts on failure)
5. Install systemd services
6. Start all services
7. Run health check
8. Print final status report

### Quick re-deploy (code changes only)

```bash
# Upload only changed modules
sshpass -p 'YOUR_VPS_PASSWORD' scp -r autoapply/ root@72.56.250.53:/opt/resumeaibot/
sshpass -p 'YOUR_VPS_PASSWORD' ssh root@72.56.250.53 "systemctl restart autoapply autoapply-worker"
```

### Manual deploy on VPS

```bash
ssh root@72.56.250.53
cd /opt/resumeaibot

# After uploading new code:
systemctl restart autoapply
systemctl restart autoapply-worker
systemctl restart resumeaibot  # only if bot code changed

# Check logs
tail -f logs/autoapply.log
tail -f logs/worker.log
tail -f bot.log
```

---

## 6. Service Costs & Recommended Amounts

| Service | Cost | Notes |
|---------|------|-------|
| **OpenAI API** | ~$10/month | ~500 tailored resume generations at gpt-4o-mini pricing (~$0.02/resume). Set $20 hard limit in dashboard. |
| **CryptoBot** | Free | Bot token from @CryptoBot. They take ~1% per transaction. No monthly fee. |
| **hh.ru API** | Free | Register OAuth app at dev.hh.ru. Free tier covers everything needed. |
| **SuperJob API** | Free | Register at api.superjob.ru. Free for moderate usage. |
| **LinkedIn** | Free | Use your own account. No paid plan needed for Easy Apply. Use conservatively. |
| **VPS** | Already running | root@72.56.250.53. Check disk space monthly: `df -h`. |
| **Domain resumeai.bot** | ~$10-15/year | Check expiry: `whois resumeai.bot \| grep Expiry`. Renew before expiry or bot webapp breaks. |
| **Telegram Bot** | Free | @BotFather. No API costs. |

**Monthly budget summary:**
- Minimum (light usage): ~$10 (OpenAI only)
- Normal (500 users): ~$15-20 (OpenAI + small buffer)
- Heavy (2000+ users): ~$40-60 (scale OpenAI accordingly)

---

## 7. Monitoring Dashboard Access

### Service status (SSH)
```bash
ssh root@72.56.250.53
systemctl status autoapply
systemctl status autoapply-worker
systemctl status resumeaibot
systemctl list-timers  # shows health-check.timer next run
```

### Live logs
```bash
# AutoApply API
tail -f /opt/resumeaibot/logs/autoapply.log

# Background worker
tail -f /opt/resumeaibot/logs/worker.log

# Health checks
tail -f /opt/resumeaibot/logs/health.log

# Error log (all exceptions)
tail -f /opt/resumeaibot/logs/errors.log

# Main bot
tail -f /opt/resumeaibot/bot.log
```

### Streamlit dashboard (if running)
```
http://72.56.250.53:8501
```

### FastAPI auto-docs
```
http://72.56.250.53:8080/docs
http://72.56.250.53:8080/redoc
```

### Health check endpoint
```
http://72.56.250.53:8080/api/health
```

### Run health check manually
```bash
ssh root@72.56.250.53
cd /opt/resumeaibot
.venv/bin/python3 health_check.py
```

---

## 8. Troubleshooting Common Issues

### AutoApply API not starting

```bash
systemctl status autoapply
journalctl -u autoapply -n 50
tail -50 /opt/resumeaibot/logs/autoapply.log
```

Common causes:
- Port 8080 already in use: `ss -tlnp | grep 8080`
- Missing .env variables: check `AUTOAPPLY_DB`, `JWT_SECRET_KEY`
- Import error in autoapply_main.py: run `python3 -c "from autoapply.autoapply_main import app"`

### Worker not processing applications

```bash
systemctl status autoapply-worker
tail -50 /opt/resumeaibot/logs/worker.log
```

Common causes:
- hh.ru OAuth tokens expired (users need to re-authorize via `/connect_hh`)
- OpenAI API key invalid or over budget
- autoapply.db locked (another process): `fuser /opt/resumeaibot/autoapply.db`

### Bot not responding in Telegram

```bash
systemctl status resumeaibot
tail -50 /opt/resumeaibot/bot.log
```

Common causes:
- BOT_TOKEN invalid or expired (check with @BotFather)
- Another bot instance running: `ps aux | grep python`
- Webhook conflict: the bot uses polling by default

### hh.ru API returning 403/401

- The user's OAuth token expired — they need to reconnect via `/connect_hh` in the bot
- Your hh.ru app may be blocked — check dev.hh.ru dashboard
- Rate limit hit: hh.ru allows ~200 applications/day per account. Check worker logs for "quota" errors.

### PDF generation fails

```bash
python3 -c "from reportlab.pdfgen import canvas; print('reportlab OK')"
```

If missing: `.venv/bin/pip install reportlab`

### Disk space low

```bash
df -h /opt/resumeaibot
# Clean old PDF resumes (generated files, safe to delete)
find /tmp/resumes -mtime +7 -name "*.pdf" -delete
# Clean old logs
find /opt/resumeaibot/logs -name "*.log" -size +50M
```

### Health check sending too many alerts

If you're getting flooded with alerts when a service is intentionally down for maintenance:
```bash
# Temporarily disable the timer
systemctl stop health-check.timer
# ... do your maintenance ...
systemctl start health-check.timer
```

### Re-run tests after fixing issues

```bash
cd /opt/resumeaibot
.venv/bin/python3 tests/test_autoapply.py
```

---

## 9. Useful Commands Quick Reference

```bash
# Restart everything
systemctl restart resumeaibot autoapply autoapply-worker

# Check all service statuses at once
for svc in resumeaibot autoapply autoapply-worker health-check.timer; do
    echo "$svc: $(systemctl is-active $svc)"
done

# Watch all logs simultaneously
tail -f /opt/resumeaibot/logs/autoapply.log \
        /opt/resumeaibot/logs/worker.log \
        /opt/resumeaibot/logs/health.log

# Check how many auto-applications were sent today
sqlite3 /opt/resumeaibot/autoapply.db \
    "SELECT COUNT(*) FROM applications WHERE date(created_at)=date('now')"

# Check active paying users
sqlite3 /opt/resumeaibot/bot.db \
    "SELECT plan, COUNT(*) FROM users GROUP BY plan"
```
