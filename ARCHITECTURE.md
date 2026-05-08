# AutoApply — System Architecture

This document is the canonical technical reference for the AutoApply system architecture.
For operations / setup instructions see [README_AUTOAPPLY.md](README_AUTOAPPLY.md).

---

## Block 1 — User Interfaces

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                          │
│                                                                 │
│  Telegram Bot              Next.js Cabinet        Telegram      │
│  (@topbestworkerbot)       (frontend/, Vercel)    Mini App      │
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
├── POST /campaigns              create campaign (engine=api_boards|career_ops)
├── GET  /campaigns              list user campaigns
├── POST /applications/{id}/review  HITL submit or discard pending_review app
├── GET  /applications           paginated list, tab filter, status filter
├── POST /auth/login             JWT issue
└── GET  /api/health             liveness probe
```

---

## Block 3 — Background Worker

```
autoapply-worker.service  (autoapply/worker.py)
│
│  every campaign tick
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
                          │
                 country_gate filter (RU blocked)
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
| Secrets exposure | none | none (`_public_portfolio()` strips all secret columns) |

**Country gate** (both engines): `is_allowed_jurisdiction()` + `resolve_company_country()` applied before any per-engine processing. RU-based vacancies never reach the scoring or application stage.

---

## Block 4 — career-ops Quality Engine Detail

```
autoapply/engines/career_ops_adapter.py
│
├── _public_portfolio(user)           strips linkedin_password_enc, password_hash, hh_token
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

---

## Block 5 — Data Layer

```
autoapply.db  (SQLite, WAL mode)
│
├── campaigns        id, user_id, name, source, engine, ...
├── applications     id, campaign_id, user_id, status, engine,
│                    match_score, cv_pdf_path, ...
├── resumes          ...
└── users            id, email, linkedin_password_enc (secret)
                                           ▲
                              never read by career_ops_adapter.py
                              (_public_portfolio strips before any use)
```

**Migrations** (additive, safe on existing DBs):
- `_MIGRATE_CAMPAIGN_ENGINE` — adds `engine TEXT DEFAULT 'api_boards'` to campaigns
- `_MIGRATE_APPLICATION_ENGINE` — adds `engine TEXT DEFAULT 'api_boards'` to applications
- `_MIGRATE_APPLICATION_CV_PDF_PATH` — adds `cv_pdf_path TEXT` to applications
- `_MIGRATE_APPLICATION_MATCH_SCORE` — adds `match_score REAL` to applications

---

## Block 6 — Frontend (Next.js)

```
frontend/app/
├── app/campaigns/new/page.tsx   engine selector UI (Speed vs Quality cards)
├── app/applications/page.tsx    4 tabs: Active | Pending Review | Archived | All
│                                engine badge (⚡/🎯), match score, Submit/Discard actions
└── lib/api.ts                   typed REST client
```

**Pending Review tab**: fetches `GET /applications?status=pending_review`.
Submit button → `POST /applications/{id}/review {action: "submit"}`.
Discard button → `POST /applications/{id}/review {action: "discard"}`.

---

## Block 7 — Health & Monitoring

```
health-check.timer  → health_check.py  (every 5 min)
  → checks: API :8080, worker heartbeat, disk space, DB size
  → alerts admin via Telegram on failure

career-ops.service  (oneshot, on-demand)
  → journalctl -u career-ops for batch logs
```

---

## Deployment

VPS: `root@72.56.250.53` — no git repo, deploy via rsync.

```bash
# Sync changed Python files
rsync -av autoapply/ root@72.56.250.53:/opt/resumeaibot/autoapply/
rsync -av vendor/career-ops/ root@72.56.250.53:/opt/resumeaibot/vendor/career-ops/

# Restart services
ssh root@72.56.250.53 "systemctl restart autoapply autoapply-worker"
```

See [docs/runbooks/upgrade-career-ops.md](docs/runbooks/upgrade-career-ops.md) for the career-ops submodule upgrade procedure.
