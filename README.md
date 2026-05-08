# ResumeAI Bot

AI-powered job search assistant and auto-apply service for **international job seekers**.
Apply to English-language jobs worldwide — automatically.

**Live:** https://resumeai-bot.ru · **Bot:** [@ResumeAIRobot](https://t.me/ResumeAIRobot)

---

## What it does

| Product | Description |
|---------|-------------|
| **Telegram Bot** | Resume builder, cover-letter generator, interview prep — bilingual EN/RU |
| **AutoApply** | Web dashboard + worker that applies to international jobs on autopilot |
| **Daily Matches** | 07:00 UTC push of top-5 curated job matches per user (Sonara-style) |
| **Referral Program** | Signed referral codes; +30 free days for referrer and new user |
| **Landing page** | Next.js marketing site (Hero, Testimonials, Pricing, FAQ) |

---

## Architecture

```
┌────────────────────────────────────────────┐
│  nginx (HTTPS :443)  — rate limiting, HSTS │
│  resumeai-bot.ru  /  www.resumeai-bot.ru   │
└───┬────────────────────┬───────────────────┘
    │ /api /app          │ / (landing)
    ▼                    ▼
┌──────────────┐   ┌──────────────────────────┐
│  FastAPI     │   │  Next.js static export   │
│  :8080       │   │  landing/index.html      │
│  autoapply   │   │  frontend/out/_next/     │
└──────┬───────┘   └──────────────────────────┘
       │
  ┌────┴────────────────────────────────────┐
  │  autoapply-worker  (background loop)    │
  │  ⚡ api_boards engine — volume apply    │
  │  🎯 career_ops engine — quality + HITL │
  │  Sources: Adzuna · Arbeitnow           │
  │           RemoteOK · The Muse          │
  └─────────────────────────────────────────┘
┌──────────────┐
│  aiogram 3   │
│  Bot :8000   │ ← Telegram webhook
│  resumeaibot │
└──────────────┘
```

**Country gate:** All job sources run through `is_allowed_jurisdiction()` before apply.
`COUNTRY_BLOCKLIST=RU,BY` — vacancies at Russian/Belarusian companies are never applied to.

**Databases:** Two SQLite files (WAL mode)
- `/opt/resumeaibot/autoapply.db` — users, campaigns, applications, portfolios, referrals
- `/opt/resumeaibot/bot.db` — Telegram bot users, credits, resume data

Full details: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Stack

| Layer | Tech |
|-------|------|
| Bot | Python 3.12 · aiogram 3 · aiosqlite |
| API | FastAPI · uvicorn · python-jose (JWT) · bcrypt |
| AI | OpenAI / OpenRouter (gpt-4o-mini default, claude-haiku-3-5 for scoring) |
| Payments | Stripe Checkout (USD) · Revolut (manual, admin-approved) |
| Encryption | Fernet (AES-128) via `cryptography` — linkedin_password_enc |
| Observability | Sentry · PostHog · Google Analytics (GA4) |
| Infra | Ubuntu 24.04 VPS · nginx · certbot (Let's Encrypt) · systemd |
| Frontend | Next.js 14 (static export) · Tailwind CSS · TypeScript |
| Quality engine | career-ops v8e554cc (Node.js PDF · OpenRouter scoring) |

---

## Project layout

```
resume-ai-bot/
├── autoapply/          # FastAPI app + worker (port 8080)
│   ├── autoapply_main.py    # ~65 API routes
│   ├── autoapply_db.py      # Async SQLite helpers (v1.12.0)
│   ├── worker.py            # Job-apply background loop (dual-engine)
│   ├── country_gate.py      # Jurisdiction blocklist enforcement
│   ├── crypto.py            # Fernet encrypt/decrypt
│   ├── config.py            # All config (env vars + pricing.json)
│   ├── engines/
│   │   └── career_ops_adapter.py  # Quality engine (scoring + HITL)
│   └── services/
│       ├── daily_matches.py       # 07:00 UTC digest cron
│       └── referral.py            # Referral code generation + validation
├── bot/                # aiogram 3 Telegram bot (port 8000)
│   ├── handlers/            # 14 feature handlers
│   ├── utils/               # Keyboards, translations, texts
│   └── config.py            # Bot-specific config
├── api/                # Bot-side FastAPI server (port 8000)
├── frontend/           # Next.js marketing site + React dashboard
│   └── app/
│       ├── page.tsx              # Landing page
│       ├── app/campaigns/        # Campaign management
│       ├── app/applications/     # HITL review + application tracker
│       ├── app/templates/        # Resume template gallery (10 templates)
│       └── app/account/refer/    # Referral share page
├── landing/            # Built Next.js output (nginx root)
├── vendor/
│   └── career-ops/     # Pinned submodule @8e554cc (PDF + scoring)
├── docs/
│   └── runbooks/
│       ├── deploy.md
│       ├── restore-db.md
│       ├── restore-portfolio.md
│       ├── incident-bot-down.md
│       ├── incident-payment-stuck.md
│       ├── incident-career-ops-stuck.md
│       └── upgrade-career-ops.md
├── scripts/
│   ├── backup_db.sh            # SQLite backup with Telegram notification
│   ├── reconcile_payments.py   # Stripe ↔ DB reconciliation
│   ├── smoke_test_payments.py  # E2E payment smoke test
│   └── check_ssl.sh            # SSL cert expiry check
├── pricing.json        # Single source of truth for plan pricing (USD)
├── requirements.txt    # Pinned production dependencies
├── deploy_all.sh       # One-command full deploy (build + sync + restart + smoke)
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
# Required: BOT_TOKEN, OPENAI_API_KEY or OPENROUTER_API_KEY,
#           STRIPE_SECRET_KEY, JWT_SECRET, LINK_SECRET

# 3. Start AutoApply API
python3 -m uvicorn autoapply.autoapply_main:app --reload --port 8080

# 4. Start bot (separate terminal)
python3 run.py

# 5. Run autoapply tests
cd autoapply && python -m pytest tests/ -q
```

---

## Deploy to production

```bash
# Full deploy (builds frontend + syncs all code + restarts services):
bash deploy_all.sh

# Code-only deploy (skip Next.js build):
bash deploy_all.sh --skip-build
```

Full details: [docs/runbooks/deploy.md](docs/runbooks/deploy.md)

---

## Required environment variables

See [`.env.example`](.env.example) for the complete annotated list.

| Variable | Purpose |
|----------|---------|
| `BOT_TOKEN` | Telegram bot token |
| `JWT_SECRET` | 64-char hex secret — signs AutoApply JWT tokens |
| `LINK_SECRET` | Shared secret — Telegram SSO link tokens (bot ↔ autoapply) |
| `OPENAI_API_KEY` or `OPENROUTER_API_KEY` | AI completions + scoring |
| `STRIPE_SECRET_KEY` | Stripe payments |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook HMAC verification |
| `ENCRYPTION_KEY` | Fernet key — encrypts `linkedin_password_enc` at rest |
| `COUNTRY_BLOCKLIST` | ISO-2 codes to block (default: `RU,BY`) |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | Adzuna job search API (free tier) |

---

## Tests

```bash
# Autoapply test suite (10 tests)
python -m pytest autoapply/tests/ -v

# Frontend type-check + build
cd frontend && npm run build
```

---

## Payments

All payments are in **USD** via Stripe Checkout or Revolut (manual).

CryptoBot (USDT) and Russian bank card methods were removed in May 2026
as part of the international pivot.

See [ARCHITECTURE.md § Block 2](ARCHITECTURE.md#block-2----api-layer) for the
full payments endpoint list.
