# CHANGELOG

## 2026-04-17 — Sprint: Conversion + i18n + Lead-Gen

### New files
| File | What changed |
|------|-------------|
| `scripts/check_i18n.py` | i18n validator — parses T.ru/T.en + RU_EN + data-i18n attrs, exits 1 on any gap |
| `scripts/email_outreach.py` | Cold-email outreach: reads data/leads.csv, AI-personalises emails, sends via SMTP, logs to data/outreach_log.csv; CAN-SPAM compliant, 50/day limit |
| `scripts/telegram_outreach.py` | Telegram outreach: posts AI-generated career tips to TG_OUTREACH_CHANNELS (max 3), logs to data/tg_outreach_log.csv, 1/day per channel |

### Modified files
| File | What changed |
|------|-------------|
| `landing/index.html` | **Hero**: new headline "Создай AI-резюме за 60 секунд", swapped CTAs (primary→@topbestworkerbot, secondary→/app); **How It Works**: 3 new steps (describe role / AI generates / download PDF); **Try it Now section** (`#try-it-now`): interactive job-title+experience form → POST /api/resume/preview → live preview with download CTA; **Pricing**: updated to Free/$0, Pro/$9.99, Unlimited/$19.99 all CTAs → @topbestworkerbot; **Sticky CTA bar**: appears 300px below hero fold, "Попробовать бесплатно/Try Free"; **Section markers** (7a): `<!-- SECTION: hero/social-proof/demo/features/how-it-works/results/testimonials/try-it-now/pricing/faq/footer -->`; **SEO**: HowTo JSON-LD added to `<head>`, meta description / og:title / og:description now switch language dynamically; **i18n**: T dict hero strings updated in both RU+EN, RU_EN dict extended with ~30 new translation entries; **i18n switcher**: localStorage save + html lang attribute + meta tags all switch reliably |
| `bot/utils/bot_translations.py` | Added `error.server_down` + `error.maintenance` keys to both 'ru' and 'en' dicts |
| `run.py` | Added `from utils.bot_translations import t as _t`; added `_get_lang_from_update()` async helper (aiosqlite language lookup, defaults 'ru'); replaced hardcoded RU strings in `global_error_handler` and `maintenance_middleware` with `_t(lang, 'error.server_down')` / `_t(lang, 'error.maintenance')` |
| `marketing_cron.py` | Added `DAILY_TIPS_EN` (7 English tips), `_pick_tip_en()`, `run_daily_marketing_en()`; added UTM params `utm_source=tg_tip&utm_medium=social&utm_campaign=daily_tip` to all links |
| `autoapply/autoapply_main.py` | Added `POST /api/resume/preview` endpoint: rate-limit 3/IP/hour, OpenRouter gpt-4o-mini, returns `{preview_html: str}`, analytics tracking wrapped in try/except |

### Pre-deploy validation
- `python3 scripts/check_i18n.py` → **✅ 211 keys, 0 gaps**
- All modified `.py` files → **✅ no syntax errors**
- `<script>` open/close tags → **✅ 16/16 balanced**
- All SECTION markers present → **✅**
