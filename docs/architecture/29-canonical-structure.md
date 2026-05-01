# 29 — Canonical Structure (эталонная структура)

Создан: 2026-05-01. Rollback-точка: git tag `pre-cleanup-2026-05`.

Это единственный источник правды о том, что должно быть где.
Любой файл вне этого списка = либо добавить в git, либо удалить с сервера.

---

## Сервер: `/opt/resumeaibot/`

```
/opt/resumeaibot/
│
├── [git-tracked files]            ← ТОЧНАЯ копия git main
│   ├── run.py                     ← entrypoint бота + API :8000
│   ├── requirements.txt
│   ├── .gitignore
│   ├── Dockerfile, docker-compose.yml
│   ├── AGENTS.md, CHANGELOG.md, PROJECT_STATUS.md
│   │
│   ├── api/                       ← FastAPI app для Telegram WebApp (порт 8000)
│   │   ├── server.py
│   │   ├── schemas.py
│   │   ├── middleware/auth.py
│   │   └── routes/{resume,cover_letter,interview,payment,stripe,user,vacancy,assistant}.py
│   │
│   ├── autoapply/                 ← AutoApply SPA + API (порт 8080)
│   │   ├── autoapply_main.py      ← FastAPI entrypoint
│   │   ├── worker.py              ← background job processor
│   │   ├── autoapply_db.py
│   │   ├── config.py
│   │   ├── english_job_engine.py
│   │   ├── ats_filler.py
│   │   ├── email_sender.py
│   │   ├── payments.py
│   │   ├── static/
│   │   │   └── app.html           ← AutoApply SPA (React/Vue, compiled)
│   │   │   [ТОЛЬКО .html/.css/.js — НИКАКИХ .py файлов в static/!]
│   │   └── templates/resume/      ← 8 HTML-шаблонов резюме
│   │
│   ├── bot/                       ← Telegram bot (aiogram)
│   │   ├── config.py
│   │   ├── database/db.py
│   │   ├── handlers/              ← все хендлеры
│   │   ├── models/user.py
│   │   ├── prompts/               ← LLM prompts
│   │   ├── services/              ← openai_service, pdf_generator, etc.
│   │   └── utils/                 ← bot_translations, keyboards, md_cleaner, texts, posthog_tracker
│   │
│   ├── scrapers/                  ← ТОЛЬКО международные площадки
│   │   ├── linkedin_applicator.py
│   │   ├── resume_cache.py
│   │   ├── resume_generator.py
│   │   └── resume_pdf_generator.py
│   │   [hh_scraper.py, hh_applicator.py, superjob_scraper.py — УДАЛЕНЫ]
│   │
│   ├── landing/                   ← статический лендинг (nginx root)
│   │   ├── index.html             ← главная (RU/EN i18n)
│   │   ├── blog/*.html            ← SEO-статьи (27 штук)
│   │   ├── resume/*.html          ← SEO-страницы по профессиям
│   │   ├── app/                   ← статические заглушки для SPA-роутов
│   │   ├── locales/{ru,en}.json
│   │   ├── privacy.html, terms.html, refund.html
│   │   ├── robots.txt, sitemap.xml
│   │   └── 404.html
│   │
│   ├── chrome_extension/          ← Chrome extension (canonic с подчёркиванием)
│   │   ├── manifest.json
│   │   ├── background.js, content.js
│   │   ├── popup.html, popup.js
│   │   └── icons/
│   │
│   ├── webapp/                    ← Telegram Mini App (Vite/React)
│   │   ├── dist/                  ← скомпилированный SPA
│   │   ├── src/                   ← исходники
│   │   ├── package.json, vite.config.ts, tsconfig.json
│   │   └── index.html
│   │
│   ├── frontend/                  ← Next.js кабинет (НЕ деплоится на этот VPS)
│   │   [деплоится отдельно — Vercel или иной хост, UNKNOWN U1]
│   │
│   ├── scripts/                   ← maintenance-скрипты
│   │   ├── backup_db.sh
│   │   ├── check_i18n.py
│   │   ├── email_drip_cron.py
│   │   └── ...
│   │
│   ├── content_marketing/         ← боты постинга контента
│   ├── marketing/scripts/         ← SEO blog generator, email drip
│   ├── seo/                       ← SEO утилиты и backlink content
│   ├── data/                      ← seo_keywords.json (leads/drafts.csv — в .gitignore)
│   ├── tests/                     ← pytest tests
│   ├── help/                      ← справочные markdown для бота
│   └── deploy/                    ← шаблоны systemd units для деплоя
│
├── .env                           ← ТОЛЬКО на сервере, никогда в git
├── .venv/                         ← ТОЛЬКО на сервере (virtualenv)
├── bot.db                         ← ТОЛЬКО на сервере (SQLite, Telegram bot)
├── autoapply.db                   ← ТОЛЬКО на сервере (SQLite, AutoApply)
├── backups/                       ← ТОЛЬКО на сервере (DB snapshots, 14-day TTL)
└── logs/                          ← ТОЛЬКО на сервере (ротация 14 дней)
    ├── autoapply.log
    ├── autoapply_api.log
    ├── worker.log
    ├── health.log
    ├── backup.log
    └── drip.log
```

---

## Что НЕЛЬЗЯ хранить на сервере вне этой структуры

| Файл/паттерн | Причина | Действие |
|---|---|---|
| `._*` файлы | macOS metadata, rsync артефакт | `find . -name '._*' -delete` |
| `*.py` в `autoapply/static/` | Публично доступны через nginx `/static` | Удалить с сервера |
| `=2.6.0`, `=7.0.0` | Битые `pip install` файлы | Удалить |
| `*.bak` | Старые бэкапы конфигов | Удалить |
| Python-файлы в корне (`start.py`, `resume.py`, …) | Дубли pre-рефакторинга | Удалить после верификации |
| Дублированный `autoapply/autoapply.db` | Второй экземпляр БД | Удалить subdir-копию |
| Systemd-файлы в корне (`autoapply.service`, …) | Дубли из `/etc/systemd/` | Удалить из корня |
| `.claude/` | Claude AI session | Удалить |
| `nginx_resumeai.conf.bak` | Старый бэкап | Удалить |
| `chrome-extension/` (с дефисом) | Дубль `chrome_extension/` | Удалить из git |

---

## Systemd units (в `/etc/systemd/system/`, не в app dir)

| Unit | Назначение | Порт/путь |
|---|---|---|
| `resumeaibot.service` | Telegram bot + API :8000 | `run.py` |
| `autoapply.service` | AutoApply FastAPI :8080 | `autoapply.autoapply_main:app` |
| `autoapply-worker.service` | Background job processor | `autoapply.worker` |
| `health-check.timer` + `.service` | Каждые 5 минут | `health_check.py` |

---

## nginx routing (resumeai-bot.ru, SSL)

| Путь | Куда | Кто отдаёт |
|---|---|---|
| `/` | `landing/index.html` | nginx static |
| `/blog/*` | `landing/blog/*.html` | nginx static |
| `/resume/*` | `landing/resume/*.html` | nginx static |
| `/api/*` | `127.0.0.1:8080` | autoapply FastAPI |
| `/app/*` | `127.0.0.1:8080` | autoapply FastAPI (SPA) |
| `/static/*` | `127.0.0.1:8080` | autoapply StaticFiles |

---

## Cron jobs (root crontab)

| Расписание | Скрипт | Назначение |
|---|---|---|
| `*/30 * * * *` | `health_monitor.py` | Быстрый мониторинг (дубль health-check.timer) |
| `0 */6 * * *` | `scripts/backup_db.sh` | Бэкап БД |
| `0 */6 * * *` | `auto_test.py` | Регрессионный тест |
| `0 10 * * *` | `marketing/scripts/email_drip_cron.py` | Email drip |
| `0 6 * * *` | `marketing/scripts/seo_blog_generator.py` | SEO блог |
| `3 6 * * *` | `acme.sh --cron` | SSL renewal (acme.sh, не certbot!) |

---

## Платформы AutoApply (только международные)

Поддерживаемые значения `platforms` в таблице `campaigns`:

| Значение | Описание |
|---|---|
| `"all"` | Все источники из `ENGLISH_JOB_SOURCES` env |
| `"english"` | Alias для `"all"` |
| `"adzuna"` | Adzuna API |
| `"themuse"` | The Muse API |
| `"arbeitnow"` | Arbeitnow API |
| `"remoteok"` | RemoteOK API |
| `"linkedin"` | LinkedIn (в разработке) |

**Legacy (hh, superjob, zarplata)** → автоматически ремапятся в `"all"` (worker.py `_LEGACY_PLATFORM_MAP`).

---

## Rollback procedure

```bash
# Локально откатиться к этой точке:
git checkout pre-cleanup-2026-05

# Восстановить сервер из rsync-слепка:
rsync -avz audit/server-snapshot-pre-cleanup/ root@72.56.250.53:/opt/resumeaibot/
systemctl restart resumeaibot autoapply autoapply-worker
```
