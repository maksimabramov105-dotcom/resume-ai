# ResumeAI Bot

AI-powered job search assistant and auto-apply service.  
**Live:** https://resumeai-bot.ru · **Bot:** [@topbestworkerbot](https://t.me/topbestworkerbot)

---

## What it does

| Product | Description |
|---------|-------------|
| **Telegram Bot** | Resume builder, cover-letter generator, interview prep — in Telegram |
| **AutoApply** | Web dashboard + worker that applies to international jobs automatically |
| **Landing page** | Next.js marketing site served via nginx |

---

## Architecture

```
┌────────────────────────────────────────────┐
│  nginx (HTTPS :443)  — rate limiting, HSTS │
│  resumeai-bot.ru  /  www.resumeai-bot.ru   │
└───┬────────────────────┬───────────────────┘
    │ /api /app /static  │ / (landing)
    ▼                    ▼
┌──────────────┐   ┌──────────────────────┐
│  FastAPI     │   │  Next.js static HTML │
│  :8080       │   │  /opt/resumeaibot/   │
│  autoapply   │   │  landing/            │
└──────┬───────┘   └──────────────────────┘
       │
  ┌────┴────────────────────┐
  │  autoapply-worker       │
  │  (background job loop)  │
  │  English job boards:    │
  │  Adzuna · Arbeitnow     │
  │  RemoteOK · The Muse    │
  └────────────────────────┘
┌──────────────┐
│  aiogram 3   │
│  Bot :8000   │ ← Telegram webhook
│  resumeaibot │
└──────────────┘
┌──────────────────────┐
│  Streamlit dashboard │ ← internal only, :8501
└──────────────────────┘
```

**Databases:** Two SQLite files (WAL mode)
- `/opt/resumeaibot/autoapply.db` — AutoApply users, campaigns, applications
- `/opt/resumeaibot/bot.db` — Telegram bot users and resumes

---

## Stack

| Layer | Tech |
|-------|------|
| Bot | Python 3.11 · aiogram 3 · aiosqlite |
| API | FastAPI · uvicorn · python-jose (JWT) · bcrypt |
| AI | OpenAI / OpenRouter (gpt-4o-mini default) |
| Payments | Stripe Checkout · CryptoBot |
| Encryption | Fernet (AES-128) via `cryptography` package |
| Observability | Sentry · PostHog · Yandex Metrika · Google Analytics |
| Infra | Ubuntu 24.04 VPS · nginx · certbot (Let's Encrypt) · systemd |
| Frontend | Next.js 14 (static export) · Tailwind |

---

## Project layout

```
resume-ai-bot/
├── autoapply/          # FastAPI app + worker (port 8080)
│   ├── autoapply_main.py    # API routes
│   ├── autoapply_db.py      # DB helpers
│   ├── worker.py            # Job-apply background loop
│   ├── crypto.py            # Fernet encrypt/decrypt
│   ├── config.py            # All config (env vars + pricing.json)
│   └── payments.py          # Stripe + CryptoBot payment logic
├── bot/                # aiogram 3 Telegram bot (port 8000)
├── api/                # Shared API helpers (bot-side)
├── frontend/           # Next.js marketing site source
├── landing/            # Built Next.js output (served by nginx)
├── ops/
│   ├── nginx/          # nginx configs (rate limiting, HTTPS)
│   └── logrotate/      # logrotate config for /opt/resumeaibot/logs/
├── scripts/
│   ├── deploy.sh           # Safe rsync deploy (never --delete-excluded)
│   ├── backup_db.sh        # SQLite backup with Telegram notification
│   ├── reconcile_payments.py # Stripe ↔ DB reconciliation
│   ├── smoke_test_payments.py # E2E payment smoke test
│   └── check_ssl.sh        # SSL cert expiry check (weekly cron)
├── docs/
│   └── runbooks/
│       ├── deploy.md
│       ├── restore-db.md
│       ├── incident-bot-down.md
│       └── incident-payment-stuck.md
├── .github/workflows/
│   ├── ci.yml              # Lint + syntax + smoke tests on every push
│   ├── deploy.yml          # Deploy to VPS on push to main
│   └── security-review.yml # Bandit + TruffleHog on PRs
├── pricing.json        # Single source of truth for plan pricing
├── requirements.txt    # Pinned production dependencies
└── .env.example        # All required env vars documented
```

---

## Local development

```bash
# 1. Clone and set up
git clone <repo> && cd resume-ai-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Copy and fill env
cp .env.example .env
# Fill in BOT_TOKEN, OPENAI_API_KEY, STRIPE_SECRET_KEY, etc.

# 3. Start AutoApply API
python3 -m uvicorn autoapply.autoapply_main:app --reload --port 8080

# 4. Start bot (separate terminal)
python3 run.py

# 5. Run smoke tests
BOT_API=http://localhost:8000 AA_API=http://localhost:8080 python3 scripts/smoke_test_payments.py
```

---

## Deploy to production

```bash
VPS_PASS='<password>' bash scripts/deploy.sh
```

Full details: [docs/runbooks/deploy.md](docs/runbooks/deploy.md)

---

## Required environment variables

See [`.env.example`](.env.example) for the complete annotated list.

Critical ones:

| Variable | Purpose |
|----------|---------|
| `BOT_TOKEN` | Telegram bot token |
| `JWT_SECRET` | 64-char hex secret for JWT signing |
| `OPENAI_API_KEY` or `OPENROUTER_API_KEY` | AI completions |
| `STRIPE_SECRET_KEY` | Stripe payments |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification |
| `ENCRYPTION_KEY` | Fernet key for linkedin_password_enc |
| `SENTRY_DSN` | Error tracking (optional but recommended) |
| `AUTOAPPLY_ENABLED` | Set `0` to pause worker without stopping service |

Generate secrets:
```bash
# JWT_SECRET
python3 -c "import secrets; print(secrets.token_hex(32))"

# ENCRYPTION_KEY (Fernet)
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Monitoring

- **Health check:** `GET https://resumeai-bot.ru/api/health`
- **Deep health:** `GET https://resumeai-bot.ru/api/health/deep`
- **Auto-restart:** `monitor.py` runs every 30 min via cron, restarts failed services (max 5 restarts/hour)
- **Alerts:** Telegram message to `ADMIN_TELEGRAM_ID` on service failure
- **SSL check:** Weekly cron via `scripts/check_ssl.sh`, alerts if cert < 21 days

---

## Incident runbooks

| Incident | Runbook |
|----------|---------|
| Bot or API down | [incident-bot-down.md](docs/runbooks/incident-bot-down.md) |
| Payment not processed | [incident-payment-stuck.md](docs/runbooks/incident-payment-stuck.md) |
| Database restore | [restore-db.md](docs/runbooks/restore-db.md) |
| Deploy | [deploy.md](docs/runbooks/deploy.md) |

---

## Pricing plans

Defined in [`pricing.json`](pricing.json) — single source of truth used by both the API and frontend.

| Plan | Daily limit | Price |
|------|------------|-------|
| Free | 3 apps/day | $0 |
| Trial | 30 apps/day | $2.99 / 14 days |
| Pro | 50 apps/day | $19.99 / month |
| Unlimited | No cap | $29.99 / month |
