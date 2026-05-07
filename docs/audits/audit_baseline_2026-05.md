# Baseline Audit — International Pivot
**Date:** 2026-05-07  
**Branch:** `claude/wonderful-carson-cc1225`  
**Scope:** All 9 architecture blocks; read-only

---

## § 1 — Russia Coupling Inventory

> Legend: `REMOVE` = must go before GA; `DEPRECATE` = keep data, stop writing; `KEEP` = not Russia-specific; `REMAP` = already re-wired, delete dead code.

| # | File | Line(s) | Identifier / String | Decision |
|---|------|---------|---------------------|----------|
| 1 | `autoapply/worker.py` | 94–100 | `_LEGACY_PLATFORM_MAP = {"hh": "all", "superjob": "all", "zarplata": "all"}` — dead remap code | REMAP (code path kept as guard; note it in migration) |
| 2 | `autoapply/worker.py` | 281 | `vacancy.get("title", "Вакансия")` — Russian fallback string | REMOVE → change to `"Vacancy"` |
| 3 | `autoapply/worker.py` | 367–369 | `notify_user()` message body in Russian: "АвтоОтклик: отправлено ещё…" | REMOVE → internationalise |
| 4 | `autoapply/payments.py` | 2, 32, 42–59 | Full CryptoBot integration; `USDT_RUB_RATE`; price_rub→USDT conversion | REMOVE (whole CryptoBot flow) |
| 5 | `autoapply/payments.py` | 305–306 | Russian user Telegram notification: "Оплата получена! Тариф…" | REMOVE |
| 6 | `autoapply/payments.py` | 313–315 | Russian admin notification: "Новая оплата AutoApply" | REMOVE |
| 7 | `autoapply/config.py` | 37–41 | `CRYPTOBOT_TOKEN`, `CRYPTOBOT_WEBHOOK_SECRET`, `CRYPTOBOT_AUTOAPPLY_TOKEN` | REMOVE env vars |
| 8 | `autoapply/autoapply_main.py` | 105 | `"headhunter.fi"` in `_JOB_URL_WHITELIST` | KEEP — headhunter.fi is a Finnish platform, not Russian |
| 9 | `autoapply/autoapply_main.py` | 252 | CSP `script-src` includes `https://vk.com` | REMOVE |
| 10 | `autoapply/autoapply_main.py` | 560–612 | `POST /api/auth/vk-login` — VK OAuth endpoint, creates `vk_XXXX@vk.autoapply` synthetic users | REMOVE (risk: orphan accounts — see §6 Risk #3) |
| 11 | `autoapply/autoapply_main.py` | 1084–1095 | Cover-letter AI prompt hardcoded `"Write a cover letter in Russian"` | REMOVE → make language-aware |
| 12 | `autoapply/autoapply_main.py` | 1437, 1471, 1475 | Demo-analyze prompt: `"salary range in rubles or 'Не указана'"`, fallback `"Вакансия проанализирована"` | REMOVE → English equivalents |
| 13 | `autoapply/autoapply_main.py` | 2135 | Help-widget system prompt: `"Ты виджет поддержки сервиса АвтоОтклик (resumeai-bot.ru)"` | REMOVE → English |
| 14 | `autoapply/autoapply_main.py` | 2159–2219 | `POST /api/admin/post-to-vk` + `VKPostRequest` model; `VK_API_TOKEN`, `VK_GROUP_ID` | REMOVE |
| 15 | `autoapply/autoapply_main.py` | 2209 | `"russian-formal"` in `VALID_TEMPLATES` list | DEPRECATE → remove from list, keep file until zero usages |
| 16 | `autoapply/autoapply_main.py` | 2342 | Interview evaluate prompt: `"Respond ONLY in Russian with valid JSON"` | REMOVE → English |
| 17 | `autoapply/autoapply_main.py` | 1259 | `POST /api/webhook/payment` (CryptoBot webhook) | REMOVE |
| 18 | `autoapply/autoapply_main.py` | 1290 | `POST /api/payment/create-invoice` (CryptoBot invoice creation) | REMOVE |
| 19 | `autoapply/autoapply_main.py` | 214 | FastAPI `description="АвтоОтклик — …"` | REMOVE → English |
| 20 | `autoapply/static/app.html` | 9–10 | VK ID SDK `<script src="https://unpkg.com/@vkid/sdk…">` | REMOVE |
| 21 | `autoapply/static/app.html` | 416 | Lang-toggle button emoji `🇷🇺` | REMOVE / revise |
| 22 | `autoapply/static/app.html` | 468–474 | `#vk-one-tap-container-login` — VK login widget | REMOVE |
| 23 | `autoapply/static/app.html` | 586, 725 | Salary `placeholder="150000"` (ruble-scale integer) | REMOVE → USD placeholder |
| 24 | `autoapply/static/app.html` | 1058 | "Pay via CryptoBot" payment option copy | REMOVE |
| 25 | `autoapply/static/app.html` | 1986 | `toLocaleTimeString('ru-RU', …)` | REMOVE → `'en-US'` or `undefined` |
| 26 | `autoapply/static/app.html` | 2118 | `toLocaleString('ru-RU')` salary formatter | REMOVE → `'en-US'` |
| 27 | `autoapply/static/app.html` | 2391 | `toLocaleDateString('ru-RU', …)` | REMOVE → `'en-US'` |
| 28 | `autoapply/static/app.html` | 2521 | VK share URL: `https://vk.com/share.php?url=…` | REMOVE |
| 29 | `frontend/app/layout.tsx` | 136–144 | Yandex Metrika tag `mc.yandex.ru/metrika/tag.js` + Yandex counter `108521982` | REMOVE |
| 30 | `pricing.json` | all | `price_rub` field in every plan | DEPRECATE (stop writing; remove in follow-up after all reads are gone) |
| 31 | `bot/config.py` | 29–35 | `RU_CARD_NUMBER`, `RU_CARD_HOLDER`, `RU_BANK_NAME` — Russian bank card payment vars | REMOVE |
| 32 | `bot/handlers/payment.py` | header | `"💎 Crypto — CryptoBot auto invoice"`, `"🇷🇺 RU Card"` payment methods | REMOVE |
| 33 | `bot/utils/keyboards.py` | 7, 33–34, 54, 80–210 | All keyboard function defaults `lang='ru'` | REMAP → change defaults to `'en'` |
| 34 | `bot/main.py` | 61–62 | `set_my_description(…, language_code="ru")` — bot description only in Russian | REMOVE → add EN; keep RU as supplementary |
| 35 | `autoapply/templates/resume/russian-formal.html` | — | Russian-language resume template | DEPRECATE (file retained; removed from VALID_TEMPLATES) |
| 36 | `content_marketing/vk_poster.py` | — | VK community posting module | REMOVE |
| 37 | `.env.example` | 34–44, 86–88 | `RU_CARD_NUMBER`, `RU_CARD_HOLDER`, `REVOLUT_TAG`, `VK_API_TOKEN`, `VK_GROUP_ID` | REMOVE |

---

## § 2 — Block-by-Block Current State

### Block 0 — nginx (Entry Point)
Config lives at `/etc/nginx/` on VPS; not tracked in repo (`ops/nginx/` directory present but contents unknown). nginx serves `resumeai-bot.ru` (a `.ru` domain — this should be the first thing discussed before an international rebrand). Routes `/api/*`, `/app/*`, `/blog/*` to AutoApply API on port 8080; `/` to static landing files. Security headers and rate limiting are in place. SSL via Let's Encrypt with auto-renew. No country-based blocking exists. **Broken/missing:** nginx config is not committed to repo — changes are made manually on VPS, creating drift risk.

### Block 1 — Landing Page (Next.js + React Dashboard)
Next.js 14 static-export marketing site. Serves the React-based AutoApply web dashboard (`frontend/out/` compiled artefacts). Has PostHog and Google Analytics (GA4) wired correctly. **Broken/Russia-coupled:** Yandex Metrika counter `108521982` is injected in `layout.tsx` on every page — a Russian state-affiliated analytics service that will deter international users and is a GDPR/privacy risk. VK share link in the dashboard HTML. Dashboard date/number formatters hardcoded to `'ru-RU'` locale. Salary input placeholder uses ruble-scale integer (150000). Front-end lang-switching has a `🇷🇺` toggle that implies the product is Russian.

### Block 2 — AutoApply API (FastAPI :8080)
~65 HTTP endpoints covering auth, campaigns, resume, jobs, payments, admin, and monitoring. JWT auth works correctly. Stripe Checkout and webhook handler are fully wired and in USD — **keep**. **Broken/Russia-coupled:** VK OAuth login endpoint (`/api/auth/vk-login`) creates synthetic `vk_XXXX@vk.autoapply` email users — live in DB. CryptoBot invoice and webhook endpoints (`/api/webhook/payment`, `/api/payment/create-invoice`) convert from `price_rub` to USDT, using `USDT_RUB_RATE`. Cover-letter AI prompt hardcoded to Russian language. Demo-analyze endpoint falls back to Russian-language strings. Interview endpoint instructs AI to respond in Russian. Help-widget system prompt identifies the product in Russian as "АвтоОтклик". `russian-formal` resume template still registered in `VALID_TEMPLATES`. VK wall-post admin endpoint exposed.

### Block 3 — AutoApply Worker (background service)
Infinite loop processing active campaigns every 300s. Four English job boards (Adzuna, Arbeitnow, RemoteOK, The Muse) — all international. Legacy CIS platform names (hh, superjob, zarplata) are silently remapped to "all" — the guard is correct but the dead DB entries with `source='hh'` or `source='superjob'` still exist in the `campaigns` table and could confuse future tooling. **Broken/Russia-coupled:** `notify_user()` sends a Russian-language Telegram message to the user. Vacancy title fallback is Russian `"Вакансия"`. **No country blocklist exists** — the worker will apply to companies domiciled in Russia if their jobs appear on international boards. No company-domicile check is implemented anywhere.

### Block 4 — Telegram Bot
Bilingual RU/EN via `bot_translations.py`. Handlers for 12 features. **Broken/Russia-coupled:** Default language throughout the entire codebase is `'ru'` — every keyboard function signature defaults to `lang='ru'`, every `get_or_create_user()` call falls back to Russian, and the bot Telegram description is only registered for `language_code="ru"`. The payment handler offers "RU Card" (Russian bank card) and "CryptoBot" as payment methods alongside Revolut and standard crypto. `RU_CARD_NUMBER`, `RU_CARD_HOLDER`, `RU_BANK_NAME` env vars are present. This entire payment method set needs to be replaced with Stripe for the international pivot.

### Block 5 — Bot API Server (FastAPI :8000)
Minimal FastAPI server receiving Telegram webhook and forwarding to aiogram. Clean — no Russia-specific coupling found. Health endpoint `/api/health` is present. No issues.

### Block 6 — Databases
Two SQLite files in WAL mode. `autoapply.db` contains `cryptobot_events` table (orphaned once CryptoBot is removed), `campaigns.source` column with possible `'hh'`/`'superjob'` values from prior users, and `autoapply_users` with VK-synthetic email rows (`vk_XXXX@vk.autoapply`). `pricing.json` has `price_rub` field on all plans — referenced in `payments.py` for CryptoBot invoice amount calculation. `bot.db` `users` table stores `language` column where existing users have `'ru'` as their locale — new default must be `'en'` going forward but existing rows need no migration (they can keep their preference). Backup is scripted via `scripts/backup_db.sh`.

### Block 7 — Monitoring & Auto-recovery
`health_check.py` checks `/api/health`, `/api/health/deep`, and Streamlit health on a 5-minute systemd timer. `monitor.py` watches systemd service status, HTTP endpoints, and disk space. `self_healer.py` handles escalation. Max 5 auto-restarts per hour. All alerts go to `ADMIN_ID` via Telegram. **No issues specific to international pivot** — monitoring is infrastructure-level and agnostic to market/language.

### Block 8 — Background Automation
`daily_reporter.py` sends daily stats to admin at 06:00 UTC. `marketing_cron.py` posts to **Telegram channel** and **VK** — VK posting will be removed. `content_marketing/vk_poster.py` is an entire VK community posting module. SSL check and DB backup scripts are clean. `scripts/reconcile_payments.py` and `scripts/smoke_test_payments.py` are for Stripe and appear clean, but need review for any CryptoBot references.

---

## § 3 — Competitor Gap Table

| Feature | ResumeAI Bot | Sonara AI | Jobright | Simplify | LazyApply | career-ops |
|---------|-------------|-----------|----------|----------|-----------|-----------|
| Auto-curated daily job matches pushed to user | **Missing** | Have | Have | Missing | Missing | Missing |
| Tailored CV/resume per job (AI-rewritten) | **Missing** | Have | Missing | Missing | Missing | Have |
| AI cover letter per job | **Have** | Have | Missing | Missing | Missing | Have |
| Job-fit / semantic match score | **Partial** (ATS keyword score only) | Have | Have | Missing | Missing | Have (10-dim) |
| One-click / background auto-apply | **Have** (worker) | Have | Have | Missing | Have | Have |
| Application volume tiers (daily limits) | **Have** | Have | Have | Missing | Have | Missing |
| Application tracker (dashboard) | **Have** | Have | Have | Have | Partial | Have |
| Chrome extension autofill | **Partial** (extension exists, limited) | Missing | Missing | Have | Missing | Missing |
| ATS form filling (Greenhouse, Lever, Workable) | **Have** (ats_filler.py) | Missing | Missing | Have | Partial | Have |
| HITL (human-in-the-loop) review step | **Missing** | Missing | Missing | Missing | Missing | Have |
| Multi-portal Playwright scraping | **Partial** (4 boards via API) | Have | Have | Missing | Have | Have |
| Lifetime pricing tier | **Missing** | Missing | Missing | Missing | Have | Missing |
| Telegram bot interface | **Have** | Missing | Missing | Missing | Missing | Missing |
| Resume PDF generation with templates | **Have** (8 templates) | Missing | Missing | Missing | Missing | Missing |
| Interview prep (STAR method) | **Have** | Missing | Missing | Missing | Missing | Missing |
| LinkedIn import | **Have** | Have | Have | Have | Missing | Missing |
| Job-board diversity (# sources) | **Partial** (4: Adzuna, Arbeitnow, RemoteOK, TheMuse) | Have (10+) | Have (20+) | Missing | Have (10+) | Have (5+) |
| Country blocklist (refuse Russian companies) | **Missing** | N/A | N/A | N/A | N/A | N/A |

**Key gaps vs. top competitors:**
1. No daily push/digest of curated matches (Sonara's core UX)
2. No per-job resume tailoring (full re-write, not just cover letter)
3. Only 4 job boards; competitors cover 10–20+
4. No lifetime tier (LazyApply differentiator)
5. No HITL review option for high-value applications

---

## § 4 — Endpoint Inventory

### Auth
| Method | Path | Tag |
|--------|------|-----|
| POST | `/api/register` | International — keep |
| GET | `/api/verify-email` | International — keep |
| POST | `/api/resend-verification` | International — keep |
| POST | `/api/forgot-password` | International — keep |
| POST | `/api/reset-password` | International — keep |
| POST | `/api/login` | International — keep |
| POST | `/api/auth/login` | International — keep |
| POST | `/api/auth/register` | International — keep |
| GET | `/api/auth/me` | International — keep |
| **POST** | **`/api/auth/vk-login`** | **Russia-only — REMOVE** |

### Campaigns
| Method | Path | Tag |
|--------|------|-----|
| POST | `/api/campaign/create` | International — keep |
| GET | `/api/campaigns` | International — keep |
| POST | `/api/campaigns` | International — keep |
| GET | `/api/campaign/{id}/status` | International — keep |
| POST | `/api/campaign/{id}/pause` | International — keep |
| POST | `/api/campaign/{id}/resume_campaign` | International — keep |
| PATCH | `/api/campaigns/{id}` | International — keep |
| DELETE | `/api/campaigns/{id}` | International — keep |

### Profile & Resume
| Method | Path | Tag |
|--------|------|-----|
| GET | `/api/user/profile` | International — keep |
| GET | `/api/user/connections` | International — keep |
| POST | `/api/user/linkedin/connect` | International — keep |
| DELETE | `/api/user/linkedin/disconnect` | International — keep |
| POST | `/api/resume/connect` | International — keep |
| POST | `/api/resume/generate-pdf` | International — keep (remove `russian-formal` from template list) |
| GET | `/api/resume/templates` | International — keep (remove `russian-formal`) |
| GET | `/api/resume/template-preview/{id}` | International — keep |
| POST | `/api/resume/import-linkedin` | International — keep |
| POST | `/api/resume/preview` | International — keep |

### Jobs & Applications
| Method | Path | Tag |
|--------|------|-----|
| GET | `/api/applications` | International — keep |
| GET | `/api/jobs/search` | International — keep |
| POST | `/api/jobs/auto-apply` | International — keep |
| GET | `/api/jobs/history` | International — keep |
| POST | `/api/generate-cover-letter` | International — keep (fix Russian prompt) |
| POST | `/api/onboarding` | International — keep |

### Payments
| Method | Path | Tag |
|--------|------|-----|
| POST | `/api/payments/create-checkout` | International — keep (Stripe USD) |
| POST | `/api/payments/webhook` | International — keep (Stripe) |
| POST | `/api/stripe-webhook` | International — keep (Stripe alias) |
| GET | `/api/payments/status` | International — keep |
| **POST** | **`/api/webhook/payment`** | **Russia-only — REMOVE (CryptoBot)** |
| **POST** | **`/api/payment/create-invoice`** | **Russia-only — REMOVE (CryptoBot)** |

### Admin
| Method | Path | Tag |
|--------|------|-----|
| POST | `/api/admin/approve-testimonial` | International — keep |
| POST | `/api/admin/generate-blog-post` | International — keep |
| POST | `/api/admin/post-to-channel` | International — keep (Telegram channel) |
| **POST** | **`/api/admin/post-to-vk`** | **Russia-only — REMOVE** |

### Public & Utility
| Method | Path | Tag |
|--------|------|-----|
| POST | `/api/demo-analyze` | International — keep (fix Russian strings) |
| GET | `/api/stats` | International — keep |
| GET | `/api/pricing` | International — keep |
| GET | `/api/health` | International — keep |
| GET | `/api/health/deep` | International — keep |
| POST | `/api/testimonials/submit` | International — keep |
| GET | `/api/testimonials` | International — keep |
| POST | `/api/help/question` | International — keep (fix Russian system prompt) |
| GET | `/api/pixel` | International — keep |
| POST | `/api/interview/evaluate` | International — keep (fix Russian AI response instruction) |

### Chrome Extension
| Method | Path | Tag |
|--------|------|-----|
| GET | `/api/extension/pending/{user_id}` | International — keep |
| POST | `/api/extension/report` | International — keep |

### Blog / App (catch-all)
| Method | Path | Tag |
|--------|------|-----|
| GET | `/blog`, `/blog/`, `/blog/{slug}` | International — keep |
| GET | `/app`, `/app/{path}` | International — keep |

**Summary: 3 endpoints to remove (VK login, 2× CryptoBot). 1 endpoint needs Russian string fixes (demo-analyze). 3 endpoints need prompt language fixes (cover-letter, interview, help).**

---

## § 5 — Handler Inventory (Telegram Bot)

| Handler file | Commands / callbacks | Language coupling | Tag |
|---|---|---|---|
| `bot/handlers/start.py` | `/start`, `/menu` | Default `lang='ru'` via DB `language` column | International — keep (fix default to `'en'`) |
| `bot/handlers/resume.py` | Resume creation flow (4 steps) | Uses `t(lang, …)` correctly | International — keep |
| `bot/handlers/cover_letter.py` | Cover letter generation | Uses `t(lang, …)` correctly | International — keep |
| `bot/handlers/interview.py` | STAR interview simulator | Uses `t(lang, …)` correctly | International — keep |
| `bot/handlers/vacancy_analysis.py` | Vacancy text analysis | Uses `t(lang, …)` correctly | International — keep |
| `bot/handlers/ai_assistant.py` | Free-form AI chat | Unknown — needs audit of prompt language | International — keep (verify prompt language) |
| `bot/handlers/payment.py` | Buy credits flow: CryptoBot + RU Card + Revolut + Stripe | **Has RU Card, CryptoBot methods** | **Russia-coupled — REMOVE RU Card + CryptoBot methods** |
| `bot/handlers/profile.py` | User profile, plan display | Uses `t(lang, …)` | International — keep |
| `bot/handlers/support.py` | Support ticket submission | Uses `t(lang, …)` | International — keep |
| `bot/handlers/checkin.py` | Daily check-in / motivation loop | Unknown — needs audit for Russian tips strings | International — keep (verify strings) |
| `bot/handlers/language.py` | `lang:ru` / `lang:en` callback handlers | Correct — handles switching | International — keep |
| `bot/handlers/tracker.py` | Manual application tracker | Uses `t(lang, …)` | International — keep |
| `bot/handlers/auto_apply.py` | AutoApply campaign status bridge | Connects to AutoApply API | International — keep |

**Summary: 1 handler to partially remove (payment.py Russian methods). All others are clean in structure but need default-language switch from `'ru'` to `'en'`.**

---

## § 6 — Top-10 Risks of Upcoming Changes

| # | Risk | Blast radius | Mitigation |
|---|------|-------------|-----------|
| 1 | **`campaigns.source` DB rows with `'hh'`/`'superjob'` values** — worker remaps them at runtime but future queries (filters, analytics) will see unrecognised source values | High — affects all active campaign queries | Add additive migration: `UPDATE campaigns SET source='all' WHERE source IN ('hh','superjob','zarplata')`. Do before removing the remap guard. |
| 2 | **VK OAuth users orphaned** — removing `/api/auth/vk-login` leaves `autoapply_users` rows with `email LIKE 'vk_%@vk.autoapply'`. They cannot log in again once the endpoint is gone. | Medium — affects only VK-registered users (unknown count) | Before removal: add a `/api/auth/vk-migrate` endpoint that converts synthetic email to a real one + password reset flow. OR send a migration email. Run `SELECT COUNT(*) FROM autoapply_users WHERE email LIKE 'vk_%@vk.autoapply'` to quantify. |
| 3 | **`cryptobot_events` table orphaned** — removing CryptoBot leaves this table in `autoapply.db`. No foreign keys; safe to leave for now. | Low — data just sits there | Document in migration; schedule a DROP in a later cleanup prompt. |
| 4 | **`price_rub` field referenced in `payments.py`** — `create_invoice()` reads `plan_info.get("price_rub")`. Removing CryptoBot before removing `price_rub` lookups causes a dead-code harmless reference; removing `price_rub` from JSON before removing the lookup causes a `None` read. | Low if ordered correctly | Order: (1) remove CryptoBot code, (2) then remove `price_rub` field from `pricing.json` in a follow-up prompt. |
| 5 | **Russian-language cover letters sent to English employers** — `/api/generate-cover-letter` prompt is hardcoded `"Write a cover letter in Russian"`. All current autoapply cover letters are going to English-language companies in Russian. | High — live user-facing bug | Fix in Block-2 prompt (P01 or P02): change to `"Write a professional cover letter in English"` |
| 6 | **Interview evaluate returns Russian JSON** — `"Respond ONLY in Russian with valid JSON"` means interview feedback is Russian for all users including English-speaking ones. | High — English users see Russian text | Same fix as above: change system instruction to English. |
| 7 | **`russian-formal` template in active use** — if any user has selected this template for PDF generation and it's removed from `VALID_TEMPLATES` without a fallback, their PDF generation silently fails or 404s. | Medium — small but real user cohort | Query `SELECT COUNT(*) FROM applications WHERE resume_used LIKE '%russian-formal%'` (or check PDF endpoint calls). Keep the file; only remove from the selectable list. |
| 8 | **Yandex Metrika collecting data from international users** — even if analytics volume is low, this is a GDPR/privacy liability and a trust signal problem for Western users. | High (reputational/legal) | Remove the YM script from `layout.tsx` in the first frontend prompt. |
| 9 | **No country blocklist in worker** — the worker will auto-apply to any vacancy regardless of the hiring company's country of domicile. Without a blocklist, Russian-company applications will be sent, violating the strategic constraint. | High — strategic/compliance | Implement blocklist in Block-3 prompt: check `company` name + `location` against a TLD/country list before calling `log_application`. |
| 10 | **Bot default language is `'ru'`** — `get_or_create_user()` sets `language='ru'` for all new users. Changing the default to `'en'` after go-live is a one-liner in `bot/database/db.py` but the change must not retroactively flip existing Russian-speaking users. | Medium — new user experience | Change `DEFAULT_LANG = 'ru'` to `DEFAULT_LANG = 'en'` in `bot/database/db.py` only (new users). Existing rows are untouched; Russian stays available as a selectable locale. |
