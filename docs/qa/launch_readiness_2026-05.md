# Launch Readiness QA Report — 2026-05

**Sign-off date:** 2026-05-08  
**Branch:** `claude/wonderful-carson-cc1225`  
**Sprint:** P13 — Pre-Launch QA  
**Status:** ✅ PASS — cleared for paid ads and public launch

---

## A. Static Code Health

| Check | Result | Notes |
|-------|--------|-------|
| `pytest autoapply/tests/` | ✅ **116/116 passed** | Fixed: `asyncio.get_event_loop().run_until_complete()` → `asyncio.run()` in 4 test files (portfolio, telegram_link, voice, applications_hub) |
| `npm run lint` | ✅ **0 errors, warnings only** | Fixed: 3 unescaped entities in `refer/page.tsx` and `campaigns/new/page.tsx` |
| `npm run build` | ✅ **clean** | Static export to `frontend/out/` |
| `grep -ri "hh\.ru\|superjob\|CRYPTOBOT_TOKEN"` code | ✅ **0 live-code hits** | Remaining refs: country_gate.py domain map (expected), worker.py unsupported-board filter (expected), test fixtures (expected) |
| `bandit -r autoapply/ bot/` HIGH severity | ✅ **0 HIGH** | Fixed: `hashlib.sha1` in `resume_tailor.py` → `usedforsecurity=False` |

### Bugs fixed in A:
1. **`asyncio.get_event_loop()` in test fixtures** — test suite failed silently when run as a full suite (passed individually). Fixed across `test_portfolio.py`, `test_telegram_link.py`, `test_voice.py`, `test_applications_hub.py`.
2. **`bot/services/payment_service.py` dead import** — `from config import CRYPTOBOT_TOKEN` would crash any call to `apply_package_credits()` since `CRYPTOBOT_TOKEN` was removed in P12. Rewrote the file removing all crypto/RUB code.
3. **`price_rub` KeyError** — `payment_service.py` referenced `pkg["price_rub"]` but `pricing.json` only has `price_usd` post-pivot. Fixed to `pkg.get("price_usd", 0.0)`.
4. **ESLint unescaped entities** — 3 raw quotes/apostrophes in TSX. Escaped with `&apos;` / `&quot;`.
5. **Bandit B324 (sha1)** — Non-cryptographic cache key flagged as HIGH. Added `usedforsecurity=False` kwarg.

---

## B. Database Integrity (VPS — live autoapply.db)

| Check | Result |
|-------|--------|
| `cryptobot_events` table dropped | ✅ gone |
| `autoapply_users.hh_token` column dropped | ✅ gone |
| `autoapply_users.hh_resume_id` column dropped | ✅ gone |
| Applications indexes | ✅ 4 indexes: `user_id`, `campaign_id`, `sent_at`, `user_status` |
| `portfolios` table present | ✅ |
| `referrals` table present | ✅ |
| `used_link_jti` table present | ✅ |

---

## C. Country Gate (Section D in spec)

| Test | Result |
|------|--------|
| `test_ru_blocked` | ✅ |
| `test_by_blocked` | ✅ |
| `test_us_allowed` | ✅ |
| `test_intl_allowed` | ✅ |
| `test_none_strict_blocked` | ✅ |
| `test_ru_domain_vacancy_is_blocked` (end-to-end) | ✅ |
| `test_us_com_vacancy_is_allowed` (end-to-end) | ✅ |
| `test_unknown_country_strict_produces_no_application` | ✅ |
| **Total** | ✅ **28/28 passed** |

---

## D. Security (Section F in spec)

| Check | Result | Notes |
|-------|--------|-------|
| JWT replay attack | ✅ `test_replay_is_rejected` passes | JTI consumed on first use, second use returns 401 |
| Malformed link token | ✅ `test_malformed_token_rejected` passes | |
| Independent JTIs don't interfere | ✅ `test_different_jtis_independent` passes | |
| Bandit HIGH severity | ✅ 0 findings | |

---

## E. Performance (Section E in spec)

| Check | Result | Target |
|-------|--------|--------|
| `/api/health/deep` p95 from VPS | ✅ **~51ms** | < 250ms |
| Both services active | ✅ resumeaibot + autoapply | |

---

## F. Marketing Readiness (Section H in spec)

| Check | Result | Notes |
|-------|--------|-------|
| `robots.txt` | ✅ **created** | `frontend/public/robots.txt` — blocks `/api/` and `/app/`, references sitemap |
| `sitemap.xml` | ✅ **created** | `frontend/public/sitemap.xml` — `/`, `/blog`, `/auth` |
| OG tags (title, description, url, type) | ✅ present | Missing `og:image` — acceptable (no cover image asset yet) |
| Twitter card | ✅ `summary_large_image` | |
| `<meta name="robots" content="index, follow">` | ✅ | |
| Canonical URL | ✅ `https://resumeai-bot.ru/` | |
| hreflang `en` + `x-default` | ✅ | |
| JSON-LD SoftwareApplication schema | ✅ | |
| JSON-LD FAQPage schema | ✅ 6 Q&As | |
| Cyrillic in frontend code | ✅ none found | `bot_translations.py` is expected bilingual |

---

## G. Observability (Section G in spec)

| Check | Result | Notes |
|-------|--------|-------|
| GA4 integration | ✅ `G-LSSCM2MPNG` wired in `layout.tsx` + consent default | |
| PostHog key | ⚠️ needs `NEXT_PUBLIC_POSTHOG_KEY` set in `.env` | Not blocking launch |
| Sentry DSN | ⚠️ needs `SENTRY_DSN` set in `.env` | Not blocking launch |

---

## H. Known Non-Blockers

1. **`og:image`** — No cover image asset. Create a 1200×630px image and add to layout metadata.
2. **PostHog + Sentry** — Keys need to be populated in VPS `.env`. Can be done post-launch.
3. **`bot_translations.py:rucard`** — Translation key present but the payment method returns 503. Harmless; clean up in next sprint.
4. **`<img>` vs `<Image />`** — ESLint warnings in `PortfolioCard.tsx` and `PublicPortfolioClient.tsx`. Performance optimization; not a launch blocker.
5. **`total_spent_rub` column** — DB column name is legacy; it now stores USD value. Rename in a future migration.

---

## Summary

| Section | Status |
|---------|--------|
| A. Static code health | ✅ PASS (5 bugs fixed) |
| B. Database integrity | ✅ PASS |
| C. Country gate | ✅ PASS (28/28 tests) |
| D. Security | ✅ PASS |
| E. Performance | ✅ PASS |
| F. Marketing readiness | ✅ PASS (robots.txt + sitemap.xml created) |
| G. Observability | ⚠️ Partial (PostHog/Sentry keys pending) |

**Overall: READY FOR LAUNCH** ✅  
5 bugs fixed, 2 new files added (robots.txt, sitemap.xml), 1 test infrastructure issue resolved.
