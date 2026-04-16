# ResumeAI Bot — Architecture Reference (AGENTS.md)

> Read this before making changes. Every rule here prevents a real bug.

---

## Project Layout

```
resume-ai-bot/
├── run.py                   # Main entrypoint — starts bot + FastAPI
├── run_checks.py            # Health check suite — run after every deploy
├── AGENTS.md                # This file
│
├── bot/                     # Telegram bot (aiogram v3)
│   ├── handlers/            # One file per feature
│   │   ├── language.py      # /language command + lang:ru / lang:en callbacks
│   │   ├── start.py         # /start, main_menu callback, admin commands
│   │   ├── resume.py        # Resume generation flow (FSM)
│   │   ├── cover_letter.py  # Cover letter flow (FSM)
│   │   ├── interview.py     # Mock interview flow (FSM)
│   │   ├── vacancy_analysis.py
│   │   ├── ai_assistant.py
│   │   ├── payment.py       # CryptoBot + manual payments
│   │   ├── profile.py       # Profile + referral
│   │   └── support.py       # Support + /help knowledge base
│   ├── utils/
│   │   ├── bot_translations.py   # SINGLE SOURCE OF TRUTH for all bot strings
│   │   ├── keyboards.py     # All InlineKeyboardMarkup factories (accept lang=)
│   │   ├── texts.py         # Legacy constants — keep for backward compat
│   │   └── md_cleaner.py
│   ├── models/user.py       # SQLAlchemy User model (users table)
│   ├── database/db.py       # init_db() + migrations + session helpers
│   └── services/            # openai_service, pdf_generator, digest, etc.
│
├── autoapply/
│   └── autoapply_main.py    # FastAPI app — web dashboard + all /api/* routes
│
├── landing/
│   └── index.html           # Single-file landing page (i18n via JS)
│
├── analytics_tracker.py     # Usage analytics (separate SQLite)
├── daily_reporter.py        # Daily/weekly Telegram reports to admin
└── maintenance.py           # Maintenance mode broadcast
```

---

## Critical Rules

### 1. Bot Strings — always use `t()`
All user-facing text in bot handlers **must** come from `bot/utils/bot_translations.py`.

```python
from utils.bot_translations import t
lang = user.language or 'ru'
await message.answer(t(lang, 'resume.ask_vacancy'))
```

- Never hardcode Russian or English strings in handlers.
- Add new keys to **both** `STRINGS['ru']` and `STRINGS['en']` together.
- `t()` falls back to Russian if a key is missing in `'en'` — but this is a bug, fix it.

### 2. Keyboards — always pass `lang`
Every keyboard factory in `keyboards.py` accepts `lang: str = 'ru'`.
Always pass the user's language:

```python
await callback.message.edit_text(text, reply_markup=main_menu_kb(lang))
```

### 3. Language detection pattern
```python
user = await get_or_create_user(callback.from_user.id)
lang = user.language or 'ru'   # 'ru' is the safe fallback
```

### 4. DB migrations — append only
Add new columns to the `_migrations` list in `bot/database/db.py`.
**Never** drop columns. **Never** change existing column types.
The migration runner is idempotent (catches exceptions from already-existing columns).

### 5. Router registration order (run.py)
```
language.router   ← FIRST (handles lang:* callbacks before start handles main_menu)
start.router
resume.router
...
```
Changing this order can break callback routing.

### 6. FSM state pattern
All multi-step flows use `aiogram.fsm`. Cancel always routes to `main_menu` callback.
The `cancel_kb(lang)` keyboard must be shown on every waiting state.

### 7. Analytics tracking
Every feature handler calls `track_feature(user_id, feature_name, db_path)`.
Wrap in `try/except Exception: pass` — analytics must never crash the bot.

### 8. Admin ID
`ADMIN_ID = int(os.getenv("ADMIN_ID", "6246429438"))` — set in `.env` on VPS.
All admin commands check `message.from_user.id != ADMIN_ID` and return early.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Telegram Bot | Python 3.11, aiogram v3, SQLite via SQLAlchemy async |
| Web Dashboard | FastAPI + uvicorn, aiosqlite, JWT auth |
| AI | OpenRouter API (GPT-4o-mini default) |
| PDF | reportlab |
| Payments | CryptoBot API + manual (card/Revolut) |
| Landing | Vanilla HTML/CSS/JS, two-tier i18n (data-i18n + RU_EN dict) |
| Deployment | VPS 72.56.250.53, systemd services, nginx reverse proxy |

---

## Deploy Checklist

```bash
# 1. Run checks before deploying
python run_checks.py

# 2. Deploy with the full script (uploads all changed files)
bash deploy_all.sh

# 3. Verify on VPS
sshpass -p '...' ssh root@72.56.250.53 "systemctl status resumeaibot"

# 4. Run checks against live API
python run_checks.py --host https://resumeai-bot.ru
```

---

## i18n — Landing Page

The landing page (`landing/index.html`) uses a two-tier system:
1. `data-i18n="key"` attributes → looked up in the `T` dict (for nav/hero elements)
2. `TEXT_SEL` CSS selector walk → text nodes replaced via `RU_EN` dict

When adding new visible text to the landing:
- If it's in a nav/hero element: add `data-i18n="your.key"` and add the key to both `T.ru` and `T.en`.
- If it's in a section body: add `'Russian text': 'English text'` to `RU_EN`.

---

## What NOT to do

- ❌ `window.location` — use `navigateTo` (N/A here, but keep in mind for web app)
- ❌ `window.alert` — use Telegram `showToast` or bot messages
- ❌ Hardcode Russian strings in bot handlers
- ❌ Add columns without adding a migration entry
- ❌ Touch `bot.db` schema directly on VPS — always use migrations
- ❌ Import `from utils.texts import ...` for new strings — use `bot_translations.t()`
- ❌ Skip `lang = user.language or 'ru'` — always default to 'ru'
