# AutoApply — System Architecture

This document is the canonical technical reference for the AutoApply system architecture.
For operations / setup instructions see [README_AUTOAPPLY.md](README_AUTOAPPLY.md).

**Version:** 1.12.0 (P12 — post-pivot cleanup)

---

## Block 1 — User Interfaces

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                          │
│                                                                 │
│  Telegram Bot              Next.js Cabinet        Telegram      │
│  (@ResumeAIRobot)          (frontend/, static)    Mini App      │
└──────────┬─────────────────────────┬──────────────────┬────────┘
           │                         │                  │
           ▼                         ▼                  ▼
   aiogram 3 (run.py)       FastAPI REST :8080     WebApp API :8000
   resumeaibot.service       autoapply.service       api/server.py
```

---

## Block 2 — API Layer

```
FastAPI :8080  (autoapply/autoapply_main.py)

── Auth ──────────────────────────────────────────────────────────
POST /api/register                  email + password sign-up
POST /api/login                     JWT issue
GET  /api/auth/me                   current user
POST /api/auth/telegram-link        Telegram SSO one-time link

── Campaigns ─────────────────────────────────────────────────────
POST /api/campaigns                 create (engine=api_boards|career_ops)
GET  /api/campaigns                 list user campaigns
PATCH/DELETE /api/campaigns/{id}    update / archive

── Applications ──────────────────────────────────────────────────
GET  /api/applications              paginated list (tab/status/date filters)
POST /api/applications/{id}/review  HITL: submit or discard pending_review

── Jobs ──────────────────────────────────────────────────────────
GET  /api/jobs/search               live vacancy search (Adzuna, RemoteOK, …)
POST /api/jobs/auto-apply           manual single-click apply

── Resume & CV ───────────────────────────────────────────────────
POST /api/resume/generate-pdf       PDF from template + profile data
GET  /api/resume/templates          list available templates (russian-formal removed)
POST /api/resume/import-linkedin    parse LinkedIn profile URL

── Payments ──────────────────────────────────────────────────────
POST /api/payments/create-checkout  Stripe Checkout (USD only)
POST /api/payments/webhook          Stripe webhook
GET  /api/payments/status           check subscription tier

── Referrals (P11) ───────────────────────────────────────────────
GET  /api/referral/stats            {code, link, invited, converted, pending}
POST /api/referral/redeem           apply referral code → free tier +30 days
POST /api/referral/confirm-conversion  mark converted_at, grant referrer +30 days

── Profile & Portfolio ───────────────────────────────────────────
GET  /api/user/profile              full profile + resume blob
GET/PUT /api/user/portfolio         public portfolio page
GET  /api/user/connections          linked accounts (LinkedIn, Telegram)

── Daily Matches (P11) ───────────────────────────────────────────
Cron 07:00 UTC: autoapply/services/daily_matches.py
  → top-5 keyword-scored vacancies pushed per user (Telegram DM + email)

── Reply Inbox ───────────────────────────────────────────────────
GET  /api/inbox/threads             paginated thread list
GET  /api/inbox/threads/{id}        thread + messages
POST /webhook/inbox                 inbound email webhook (HMAC-verified)

── Public / Utility ──────────────────────────────────────────────
GET  /api/stats                     public counters (?window=24h|7d|30d|all)
GET  /api/health                    liveness probe
GET  /api/health/deep               DB + worker heartbeat
POST /api/testimonials/submit       user-submitted review
GET  /api/testimonials              approved testimonials
POST /api/demo-analyze              anonymous vacancy analysis
POST /api/help/question             AI help-widget (no Russian prompts)
POST /api/interview/evaluate        STAR interview scoring
```

---

## Block 3 — Background Worker

```
autoapply-worker.service  (autoapply/worker.py)
│
│  every campaign tick (WORKER_INTERVAL=300s default)
│  ┌──────────────────────────────────────────────────────────────┐
│  │              campaign.engine routing                         │
│  │                                                              │
│  │   engine = 'api_boards'               engine = 'career_ops' │
│  │        │                                      │             │
│  │        ▼                                      ▼             │
│  │  ⚡ Speed Engine                     🎯 Quality Engine       │
│  │  (api_boards path)                  career_ops_adapter.py   │
│  │                                                             │
│  └──────────────────────────────────────────────────────────────┘
```

### Engine variants: api_boards (volume) vs career_ops (quality)

The worker routes each campaign to one of two sibling engines. They share the same
vacancy scrapers, country gate, and duplicate-check logic; they differ in what happens
after a vacancy passes those gates.

```
                  vacancies from scrapers
                  (Adzuna · RemoteOK · Arbeitnow · The Muse)
                          │
                 country_gate filter
                 (COUNTRY_BLOCKLIST=RU,BY; STRICT_DOMICILE=1)
                          │
              duplicate check (already applied?)
                          │
             ┌────────────┴────────────┐
             │                         │
    engine='api_boards'       engine='career_ops'
             │                         │
      ⚡ Speed path             🎯 Quality path
             │                         │
    ATSFiller.apply()         score_vacancy()  ◄── OpenRouter / OpenAI
             │                 composite 0-10
             │                         │
             │              score ≥ MIN_SCORE (5.5)?
             │                  yes         no
             │                   │           │
             │           generate_cv_pdf()  skip
             │           node generate-pdf.mjs
             │                   │
             │           status='pending_review'
             │           log_application()
             │                   │
             │           user reviews in dashboard
             │           POST /applications/{id}/review
             │                   │
             │             action='submit'?
             │                yes     no
             │                 │       │
    status='sent'        ATSFiller  status='rejected'
    log_application()    .apply()
```

**Key properties:**

| Property | api_boards | career_ops |
|----------|-----------|------------|
| Target portals | Adzuna, RemoteOK, Arbeitnow, The Muse | Greenhouse, Ashby, Lever, company portals |
| Throughput | up to 50 apps/day | limited by scoring cost + user review time |
| AI scoring | no | yes — 6 dimensions, weighted composite 0-10 |
| PDF generation | no | yes — `node vendor/career-ops/generate-pdf.mjs` |
| Human review step | no | **yes** — HITL required before submit |
| Application status | `sent` | `pending_review` → `sent` or `rejected` |
| Secrets exposure | none | none (`_public_portfolio()` strips password_hash + linkedin_password_enc) |

**Country gate** (both engines): `is_allowed_jurisdiction()` + `resolve_company_country()` applied
before any per-engine processing. Vacancies from blocklisted jurisdictions never reach scoring
or application stage.

---

## Block 4 — career-ops Quality Engine Detail

```
autoapply/engines/career_ops_adapter.py
│
├── _public_portfolio(user)           strips linkedin_password_enc, password_hash
├── score_vacancy(vacancy, portfolio) → {composite_score, dimensions, top_strengths, ...}
│   └── _call_openai()                OpenRouter first (claude-haiku-3-5), OpenAI fallback
├── _build_cv_html()                  minimal ATS HTML with score badge
├── generate_cv_pdf(html, ...)        subprocess: node vendor/career-ops/generate-pdf.mjs
│                                     returns path or None if Node.js unavailable
├── run_batch(campaign, vacancies, user, db_path)
│   ├── country gate
│   ├── duplicate check
│   ├── score_vacancy
│   ├── generate_cv_pdf  (if score ≥ MIN_SCORE_FOR_PDF)
│   └── log_application(status='pending_review', engine='career_ops')
└── submit_application(app_id, user, db_path)
    ├── get_application_by_id
    ├── ATSFiller.apply()
    └── update_application_after_review(status='sent')
```

**Vendor submodule** (`vendor/career-ops`, pinned to `8e554cc`):

```
vendor/career-ops/
├── generate-pdf.mjs          ← called directly as Node subprocess
├── batch/batch-runner.sh     ← optional sidecar (runs claude -p workers)
├── modes/oferta.md           ← scoring rubric reference
└── docs/ARCHITECTURE.md      ← upstream architecture doc
```

**Optional sidecar** (`ops/systemd/career-ops.service`): runs as isolated `careerops`
user with `ProtectSystem=strict`. Only needed for full `batch-runner.sh` CLI mode.
The Python adapter does not require it.

See [docs/runbooks/upgrade-career-ops.md](docs/runbooks/upgrade-career-ops.md) for
the submodule upgrade procedure, and
[docs/runbooks/incident-career-ops-stuck.md](docs/runbooks/incident-career-ops-stuck.md)
for HITL queue recovery.

---

## Block 5 — Data Layer

```
autoapply.db  (SQLite 3.45+, WAL mode)
│
├── autoapply_users  id, email, password_hash, plan, stripe_customer_id,
│                    linkedin_email, linkedin_password_enc, resume_text,
│                    is_verified, consent_at, view_prefs, referral_free_until
│                    (hh_token / hh_resume_id DROPPED in P12)
├── campaigns        id, user_id, job_title, engine, status, platforms, ...
├── applications     id, campaign_id, user_id, status, engine,
│                    match_score, cv_pdf_path, company_country, ...
│                    status values: sent | pending_review | rejected | interview | offer
├── vacancies_cache  short-lived cache keyed by vacancy_id
├── referrals        referrer_id, new_user_id, created_at, converted_at
├── portfolios       public portfolio pages (/p/{handle})
├── portfolio_assets photos / files attached to portfolio
├── portfolio_links  social / messenger / website links
├── app_threads      reply-inbox email threads
├── app_messages     individual email messages per thread
├── email_drip       onboarding email sequence state
├── email_tokens     one-time verify / reset tokens
├── testimonials     approved + pending user reviews
├── web_generations  analytics: resume/cover-letter generation events
├── page_views       lightweight page view log
├── rate_limits      per-key cooldown table (keyed by "type:ip")
├── user_links       telegram_id → autoapply_user_id SSO mapping
└── used_link_jti    replay-protection for SSO link tokens

bot.db  (SQLite, WAL mode)
└── users            telegram_id, language ('en'|'ru'), credits, ...
```

**Schema version:** `autoapply_db.__version__ = "1.12.0"`

**Migrations in init_db()** (all wrapped, safe on existing DBs):
| Migration | What it does |
|-----------|-------------|
| `_MIGRATE_IS_VERIFIED` | ADD COLUMN is_verified to autoapply_users |
| `_MIGRATE_CONSENT_AT` | ADD COLUMN consent_at |
| `_MIGRATE_STRIPE_CUSTOMER_ID` | ADD COLUMN stripe_customer_id |
| `_MIGRATE_COMPANY_COUNTRY` | ADD COLUMN company_country to applications |
| `_MIGRATE_USER_STATUS` | ADD COLUMN user_status to applications |
| `_MIGRATE_WITHDRAWN_AT` | ADD COLUMN withdrawn_at |
| `_MIGRATE_LAST_USER_ACTION` | ADD COLUMN last_user_action_at |
| `_MIGRATE_VIEW_PREFS` | ADD COLUMN view_prefs to autoapply_users |
| `_MIGRATE_CAMPAIGN_ENGINE` | ADD COLUMN engine DEFAULT 'api_boards' to campaigns |
| `_MIGRATE_APPLICATION_ENGINE` | ADD COLUMN engine to applications |
| `_MIGRATE_APPLICATION_CV_PDF_PATH` | ADD COLUMN cv_pdf_path |
| `_MIGRATE_APPLICATION_MATCH_SCORE` | ADD COLUMN match_score REAL |
| `_MIGRATE_USER_REFERRAL_FREE` | ADD COLUMN referral_free_until |
| `_MIGRATE_DROP_HH_TOKEN` *(P12)* | DROP COLUMN hh_token (0 non-null rows confirmed) |
| `_MIGRATE_DROP_HH_RESUME_ID` *(P12)* | DROP COLUMN hh_resume_id |
| `_MIGRATE_DROP_CRYPTOBOT_EVENTS` *(P12)* | DROP TABLE IF EXISTS cryptobot_events |

---

## Block 6 — Frontend (Next.js 14 static export)

```
frontend/app/
├── page.tsx                         marketing landing (Hero, HowItWorks, DemoVideo,
│                                    TrustSection, Testimonials, TrackerPreview,
│                                    Pricing, CtaSection, FAQ)
├── app/campaigns/new/page.tsx       engine selector UI (Speed vs Quality cards)
├── app/applications/page.tsx        4 tabs: Active | Pending Review | Archived | All
│                                    engine badge (⚡/🎯), match score, Submit/Discard
├── app/templates/page.tsx           resume template gallery (10 templates, 3 popular)
├── app/account/refer/page.tsx       referral share page (P11)
└── lib/api.ts                       typed REST client (api.get / api.post)
```

**Build artefact:** `frontend/out/` (rsync'd to `/opt/resumeaibot/frontend/out/` on VPS)
**Landing HTML:** `landing/index.html` must always match `frontend/out/index.html` —
generated together by `bash deploy_all.sh` (Step 1 builds then copies).

---

## Block 7 — Health & Monitoring

```
health-check.timer  → health_check.py  (every 5 min)
  → checks: API :8080, worker heartbeat, disk space, DB size
  → alerts admin via Telegram on failure

self_healer.py      → auto-restart services, escalate to admin
monitor.py          → systemd unit status, HTTP endpoints, disk
```

---

## Deployment

**VPS:** `root@72.56.250.53` — no git repo, always deploy via `bash deploy_all.sh`.

The script builds Next.js, syncs all seven source trees atomically, restarts services,
and runs a smoke test:

```bash
# Full deploy (builds frontend + syncs everything):
bash deploy_all.sh

# Skip the Next.js build (code-only change, no frontend edits):
bash deploy_all.sh --skip-build

# Skip tests (emergency hotfix):
bash deploy_all.sh --skip-tests
```

**What deploy_all.sh syncs (in order):**
1. `frontend/out/` → `/opt/resumeaibot/frontend/out/` (compiled JS/CSS chunks)
2. `landing/` → `/opt/resumeaibot/landing/` (HTML served at `/`)
3. `bot/` → `/opt/resumeaibot/bot/` (all handlers, utils, services)
4. `api/` → `/opt/resumeaibot/api/` (routes, middleware)
5. `autoapply/` → `/opt/resumeaibot/autoapply/`
6. Root-level files: `run.py`, `analytics_*.py`, `daily_reporter.py`, etc.
7. Restarts `resumeaibot` + `autoapply` services
8. Smoke tests: landing 200, JS chunk 200, `/api/stats` 200

**Runbooks:**
- [deploy.md](docs/runbooks/deploy.md) — standard release procedure
- [incident-bot-down.md](docs/runbooks/incident-bot-down.md) — bot crash recovery
- [incident-payment-stuck.md](docs/runbooks/incident-payment-stuck.md) — payment issues
- [incident-career-ops-stuck.md](docs/runbooks/incident-career-ops-stuck.md) — HITL queue stuck
- [restore-db.md](docs/runbooks/restore-db.md) — DB restore from backup
- [restore-portfolio.md](docs/runbooks/restore-portfolio.md) — portfolio data recovery
- [upgrade-career-ops.md](docs/runbooks/upgrade-career-ops.md) — bump vendor/career-ops pin
