#!/usr/bin/env python3
"""
backlink_generator.py — Generates SEO backlink content
Saves files to seo/backlink_content/ ready to post

Run: python3 seo/backlink_generator.py
"""
import os
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "backlink_content"
OUTPUT_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
# Content definitions
# Note: triple-quotes inside content blocks are written as \" \" \"
# to avoid Python string termination issues.
# ─────────────────────────────────────────────

def _github_awesome_telegram_bots_pr() -> str:
    return (
        "# PR: Add ResumeAI — AI career bot to awesome-telegram-bots\n\n"
        "## Summary\n\n"
        "Adding **ResumeAI** (@topbestworkerbot) to the Career / Productivity section.\n\n"
        "## What it does\n\n"
        "ResumeAI is a Telegram bot that combines two tools for job seekers:\n\n"
        "1. **AI Resume Builder** — generates a tailored resume for each specific vacancy in 30 seconds "
        "using GPT-4. The bot analyzes the job description and produces a matching PDF resume.\n"
        "2. **AutoApply** — automatically sends job applications to hh.ru, SuperJob, LinkedIn, and Indeed "
        "while the user sleeps. Supports filters by salary, keywords, location, and experience level.\n\n"
        "Free plan: 3 applications per day. Paid plans start at 499 RUB/month.\n\n"
        "## README addition (paste into the Career section)\n\n"
        "```markdown\n"
        "- [@topbestworkerbot](https://t.me/topbestworkerbot) — AI-powered career assistant. "
        "Generates tailored resumes in 30 seconds and auto-applies to jobs on hh.ru, LinkedIn, Indeed. "
        "Free plan available.\n"
        "```\n\n"
        "## Why this belongs here\n\n"
        "- Active bot with real users\n"
        "- Open source stack: Python, aiogram 3, FastAPI, OpenAI API\n"
        "- Solves a real problem — manual job applications are time-consuming\n"
        "- Integrates with major job boards (hh.ru API, SuperJob API)\n\n"
        "Bot link: https://t.me/topbestworkerbot\n"
        "Website: https://resumeai.bot\n"
    )


def _github_awesome_ai_tools_pr() -> str:
    return (
        "# PR: Add ResumeAI to awesome-ai-tools — AI career automation\n\n"
        "## Summary\n\n"
        "Submitting **ResumeAI** (https://resumeai.bot) for inclusion in the Job Search / Career Automation category.\n\n"
        "## Tool details\n\n"
        "**ResumeAI** is an AI-powered Telegram bot that automates the job search process end-to-end.\n\n"
        "**Core AI features:**\n"
        "- GPT-4 based resume tailoring — reads the job description, extracts requirements, "
        "and writes a targeted resume in the candidate's voice\n"
        "- PDF generation with clean formatting (reportlab)\n"
        "- Cover letter generation (optional)\n"
        "- Interview prep Q&A based on the specific role\n\n"
        "**Automation features:**\n"
        "- Scrapes hh.ru and SuperJob via official APIs\n"
        "- Applies to matching vacancies automatically\n"
        "- LinkedIn Easy Apply automation via Playwright\n"
        "- Configurable filters: salary range, keywords, blacklist companies, experience level\n\n"
        "**Tech stack:** Python 3.11, aiogram 3, FastAPI, OpenAI API, Playwright, SQLite, systemd\n\n"
        "**Links:**\n"
        "- Bot: https://t.me/topbestworkerbot\n"
        "- Web app: https://resumeai.bot/app\n"
        "- Category: Career Tools / AI Productivity\n\n"
        "## README addition (paste into Job Search / Career section)\n\n"
        "```markdown\n"
        "- [ResumeAI](https://resumeai.bot) - AI Telegram bot that writes tailored resumes per vacancy "
        "and auto-applies to jobs on hh.ru, LinkedIn, Indeed. "
        "[@topbestworkerbot](https://t.me/topbestworkerbot)\n"
        "```\n"
    )


def _reddit_post_en() -> str:
    return (
        "# Reddit Post — r/jobs (or r/GetEmployed)\n\n"
        "**Title:** I sent 300 job applications in one week without losing my mind "
        "— here's what I used (with actual results)\n\n"
        "---\n\n"
        "After getting laid off in January, I faced the classic job search grind: copy resume, "
        "tweak cover letter, fill out the same form for the 40th time, repeat. "
        "By day three I was already burned out before even getting a single callback.\n\n"
        "I'm a developer, so I did what developers do — I automated it.\n\n"
        "**What I built (and then turned into a Telegram bot):**\n\n"
        "The core insight is that most applications fail because of a mismatch between your resume "
        "and the job description. Recruiters spend 6 seconds on a resume. If your keywords don't match "
        "their ATS filters, you're invisible.\n\n"
        "So I wrote a script that:\n"
        "1. Takes a job description\n"
        "2. Extracts the key requirements and skills\n"
        "3. Rewrites my resume to match — keeping everything truthful but reordering priorities "
        "and adding relevant keywords\n"
        "4. Generates a clean PDF\n"
        "5. Submits via the job board's API or form automation\n\n"
        "**The results after 7 days:**\n\n"
        "- 312 applications sent (hh.ru + LinkedIn + Indeed)\n"
        "- 47 profile views from recruiters\n"
        "- 18 callbacks / messages\n"
        "- 12 actual interview invitations\n"
        "- 3 offers received (took the second one)\n\n"
        "**What I used:**\n\n"
        "The automation part runs as a Telegram bot now — @topbestworkerbot — if you want to try it "
        "without setting anything up yourself. Free plan gives 3 auto-applications per day which is "
        "enough to test it.\n\n"
        "The resume tailoring is GPT-4 under the hood. You paste your base resume once, and for every "
        "vacancy it rewrites the bullet points to match. Not fabricating experience — just presenting "
        "the same experience in the language the recruiter is looking for.\n\n"
        "**The honest caveats:**\n\n"
        "- This works better in markets where volume matters (hh.ru in Russia is ideal)\n"
        "- LinkedIn has rate limits — the bot is conservative to avoid account flags\n"
        "- Quality matters more than quantity for senior roles — I'd still write those manually\n\n"
        "Happy to answer questions about the technical approach or the job search strategy.\n\n"
        "---\n\n"
        "*Relevant links: [@topbestworkerbot](https://t.me/topbestworkerbot) on Telegram, "
        "[resumeai.bot](https://resumeai.bot) for the web version*\n"
    )


def _reddit_post_ru() -> str:
    return (
        "# Reddit Post — r/russia или r/Pikabu-style (ru-сообщества)\n\n"
        "**Заголовок:** Разослал 300 откликов за неделю и получил 12 собеседований — рассказываю как\n\n"
        "---\n\n"
        "После сокращения в феврале столкнулся с типичной ситуацией: каждый день вручную редактировать "
        "резюме, писать сопроводительные письма, заполнять одни и те же формы на hh.ru. "
        "К третьему дню уже хотелось всё бросить.\n\n"
        "Я разработчик, поэтому сделал что умею — автоматизировал.\n\n"
        "**Что получилось:**\n\n"
        "Написал скрипт, который:\n"
        "1. Берёт описание вакансии\n"
        "2. Определяет ключевые требования и навыки\n"
        "3. Переписывает резюме под эту конкретную вакансию — не придумывает опыт, "
        "а расставляет акценты под требования\n"
        "4. Генерирует PDF\n"
        "5. Отправляет отклик через API hh.ru или Playwright\n\n"
        "Потом оформил это в Telegram бот — @topbestworkerbot\n\n"
        "**Результаты за 7 дней:**\n\n"
        "- 312 откликов (hh.ru + SuperJob + LinkedIn)\n"
        "- 18 обратных звонков от рекрутеров\n"
        "- 12 приглашений на собеседование\n"
        "- 3 оффера\n\n"
        "**Как работает резюме-тейлоринг:**\n\n"
        "Загружаете базовое резюме один раз. Для каждой вакансии GPT-4 переписывает буллет-пункты так, "
        "чтобы они совпадали с языком вакансии. ATS-системы у крупных работодателей отсеивают резюме "
        "по ключевым словам — это их и обходит.\n\n"
        "**Бесплатно:** 3 автооткликов/день — хватит попробовать.\n\n"
        "Пишите вопросы, расскажу больше о технической реализации или стратегии поиска.\n\n"
        "---\n\n"
        "*Бот: @topbestworkerbot | Сайт: resumeai.bot*\n"
    )


def _medium_article_en() -> str:
    return (
        "# Medium Article\n\n"
        "**Title:** I Automated My Job Search and Got 12 Interviews in 7 Days\n\n"
        "**Subtitle:** How I built a system that sends tailored applications while I sleep "
        "— and why it actually worked\n\n"
        "---\n\n"
        "The job search in 2024 is broken.\n\n"
        "Job boards have hundreds of listings. Recruiters skim resumes for six seconds. "
        "ATS systems reject 75% of candidates before a human ever reads the application. "
        "And yet the advice remains the same: 'customize each application individually.'\n\n"
        "That's mathematically impossible at the scale needed to land a job quickly. "
        "So I decided to automate it properly.\n\n"
        "## The Problem With Mass Applying\n\n"
        "I want to be clear about something: sending the same resume to 500 jobs doesn't work. "
        "I know because I tried it in 2022 and got zero callbacks.\n\n"
        "The issue is keyword matching. When a job description says 'experience with distributed systems' "
        "and your resume says 'worked on backend microservices architecture,' an ATS might score you lower "
        "than a candidate who literally copy-pasted the job requirements into their resume.\n\n"
        "The solution isn't to be dishonest. It's to translate your real experience into the recruiter's "
        "language — consistently, at scale.\n\n"
        "## What I Built\n\n"
        "I spent about two weeks building a pipeline:\n\n"
        "**Step 1: Scraping** — Pull fresh vacancies from hh.ru (Russia's largest job board), SuperJob, "
        "and LinkedIn using their official APIs. Filter by keywords, salary range, and experience level.\n\n"
        "**Step 2: Resume tailoring** — For each vacancy, send the job description + my base resume to "
        "GPT-4 with a prompt that says: 'Rewrite this resume to highlight experience relevant to this role. "
        "Do not fabricate anything. Reorder and rephrase existing bullet points to match the job's language.'\n\n"
        "**Step 3: PDF generation** — Convert the tailored text to a clean one-page PDF using reportlab.\n\n"
        "**Step 4: Auto-apply** — Submit via the job board's API where available (hh.ru has a great API), "
        "or via Playwright form automation for sites without APIs.\n\n"
        "**Step 5: Tracking** — Log every application to SQLite with status, timestamps, and any recruiter responses.\n\n"
        "## The Results\n\n"
        "Over 7 days running the system:\n\n"
        "- 312 applications sent\n"
        "- 47 profile views from recruiters\n"
        "- 18 recruiter messages/calls\n"
        "- 12 interview invitations\n"
        "- 3 job offers\n\n"
        "I accepted an offer from a company I genuinely wanted to work at. "
        "The salary was 23% higher than my previous role.\n\n"
        "## What Surprised Me\n\n"
        "**The tailoring actually matters.** I ran an A/B test for the first 50 applications: "
        "25 with tailored resumes, 25 with my generic resume. Tailored: 8 callbacks. Generic: 1 callback.\n\n"
        "**Volume is necessary but not sufficient.** The combination of volume AND personalization is what worked.\n\n"
        "**Speed matters.** Applications submitted within 1-2 hours of a vacancy posting have significantly "
        "higher callback rates. My system checks for new postings every 30 minutes.\n\n"
        "## The Ethical Question\n\n"
        "Is this cheating?\n\n"
        "I don't think so. Every word in my resume is true. I'm not inflating my experience — "
        "I'm presenting it in the vocabulary the recruiter uses. "
        "The tailoring is closer to good writing than deception.\n\n"
        "## How to Try It\n\n"
        "I packaged this into a Telegram bot — [@topbestworkerbot](https://t.me/topbestworkerbot) — "
        "so you don't need to set up the infrastructure yourself. "
        "You upload your base resume, configure filters, and it runs automatically. "
        "Free plan: 3 applications per day.\n\n"
        "The full web version is at [resumeai.bot](https://resumeai.bot).\n\n"
        "---\n\n"
        "*Have questions about the technical implementation or the job search strategy? Leave a comment.*\n"
    )


def _devto_article_en() -> str:
    # Code blocks use single-backtick fences to avoid triple-quote collision
    lines = [
        "# Dev.to Article",
        "",
        "**Title:** I Built a Job Application Bot With Python, FastAPI, and GPT-4 — Here's the Architecture",
        "",
        "**Tags:** python, automation, openai, telegrambot",
        "",
        "---",
        "",
        "After getting laid off, I built a system to automate my job search. "
        "It ended with 12 interviews in 7 days. This post covers the technical architecture.",
        "",
        "## Stack",
        "",
        "- **Python 3.11** — main language",
        "- **aiogram 3** — Telegram bot framework (async, excellent)",
        "- **FastAPI** — REST API for the web dashboard",
        "- **OpenAI API (GPT-4)** — resume tailoring",
        "- **Playwright** — browser automation for sites without APIs",
        "- **reportlab** — PDF generation",
        "- **SQLite + aiosqlite** — storage (simple, works fine at this scale)",
        "- **systemd** — process management on VPS",
        "",
        "## The Resume Tailoring Prompt",
        "",
        "The core of the system is a single well-engineered prompt:",
        "",
        "```python",
        'TAILORING_PROMPT = ("""',
        "    You are an expert resume writer. Given a base resume and a job description:",
        "    1. Identify the top 5-7 skills/requirements in the job description",
        "    2. Rewrite the resume's experience bullets to use the same language and keywords",
        "    3. Do NOT add experience that doesn't exist in the base resume",
        "    4. Keep the same factual content — only rephrase and reorder",
        "    5. Prioritize the most relevant experience first",
        "    6. Output only the final resume text, no commentary",
        "",
        "    Base Resume: {resume}",
        "    Job Description: {job_description}",
        '""")',
        "```",
        "",
        "The key constraint is 'do not add experience that doesn't exist.' "
        "This keeps it honest while dramatically improving keyword matching.",
        "",
        "## hh.ru API Integration",
        "",
        "hh.ru (Russia's largest job board) has a solid REST API:",
        "",
        "```python",
        "async def search_vacancies(query, area='1', per_page=20, salary_from=None):",
        "    params = {",
        '        "text": query,',
        '        "area": area,',
        '        "per_page": per_page,',
        '        "order_by": "publication_time",',
        "    }",
        "    if salary_from:",
        '        params["salary"] = salary_from',
        '        params["only_with_salary"] = "true"',
        "    async with aiohttp.ClientSession() as session:",
        '        async with session.get("https://api.hh.ru/vacancies", params=params) as resp:',
        "            data = await resp.json()",
        '            return data.get("items", [])',
        "```",
        "",
        "Applying requires OAuth but the API is well-documented and the rate limits are reasonable.",
        "",
        "## PDF Generation",
        "",
        "reportlab for clean single-page PDFs:",
        "",
        "```python",
        "from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer",
        "",
        "def generate_pdf(text, name, output_path):",
        "    doc = SimpleDocTemplate(output_path)",
        "    styles = getSampleStyleSheet()",
        "    story = [Paragraph(name, styles['Title']), Spacer(1, 12)]",
        "    for line in text.split('\\n'):",
        "        if line.strip():",
        "            story.append(Paragraph(line, styles['Normal']))",
        "    doc.build(story)",
        "```",
        "",
        "## Health Monitoring",
        "",
        "Every 5 minutes, a systemd timer runs a health check that verifies:",
        "- Both SQLite databases respond",
        "- FastAPI is up on port 8080",
        "- hh.ru API is reachable",
        "- Disk space > 1GB",
        "- All systemd services active",
        "",
        "On failure: auto-restart attempt, then Telegram alert to admin.",
        "",
        "## What I Learned",
        "",
        "1. **Async everything** — the bot handles concurrent users, aiohttp + aiosqlite are essential",
        "2. **Idempotency matters** — track applied vacancies to avoid duplicates",
        "3. **Rate limit respect** — hh.ru will block you if you hammer their API. 1-2 req/sec is safe.",
        "4. **Playwright is slow** — use native APIs where possible, browser automation only as fallback",
        "",
        "## Try It",
        "",
        "The bot is live at [@topbestworkerbot](https://t.me/topbestworkerbot). "
        "Web dashboard at [resumeai.bot](https://resumeai.bot).",
        "",
        "Questions about the implementation? Drop them in the comments.",
        "",
    ]
    return "\n".join(lines)


def _habr_article_ru() -> str:
    lines = [
        "# Habr.com — Техническая статья",
        "",
        "**Заголовок:** Как я автоматизировал поиск работы с помощью Python, GPT-4 и hh.ru API",
        "",
        "**Хабы:** Python, Карьера в IT, OpenAI, Автоматизация",
        "",
        "---",
        "",
        "После сокращения у меня было два варианта: методично рассылать резюме вручную, "
        "или один раз потратить неделю на автоматизацию и потом рассылать по 50 откликов в день без усилий. "
        "Я выбрал второй вариант.",
        "",
        "Результат: 312 откликов за 7 дней, 12 приглашений на собеседование, 3 оффера.",
        "",
        "## Архитектура системы",
        "",
        "```",
        "Telegram Bot (aiogram 3)",
        "       |",
        "       +-- FastAPI REST API (порт 8080)",
        "       |       +-- /api/vacancies  — список найденных вакансий",
        "       |       +-- /api/apply      — отправить отклик",
        "       |       +-- /api/health     — мониторинг",
        "       |",
        "       +-- Background Worker",
        "       |       +-- Парсинг hh.ru каждые 30 минут",
        "       |       +-- Генерация резюме через OpenAI",
        "       |       +-- Автоотклик через hh.ru API",
        "       |",
        "       +-- SQLite (aiosqlite)",
        "               +-- users",
        "               +-- vacancies",
        "               +-- applications",
        "               +-- resumes",
        "```",
        "",
        "Деплой на VPS с systemd: три сервиса (бот, API, воркер) + таймер health check каждые 5 минут.",
        "",
        "## Ядро системы: тейлоринг резюме",
        "",
        "Главная проблема массовой рассылки — одно и то же резюме работает плохо. "
        "ATS-системы крупных компаний фильтруют кандидатов по совпадению ключевых слов "
        "с требованиями вакансии.",
        "",
        "Решение: для каждой вакансии генерировать отдельную версию резюме.",
        "",
        "```python",
        "async def generate_tailored_resume(base_resume, vacancy):",
        "    prompt = f'''",
        "Ты — опытный HR-консультант и карьерный коуч.",
        "Задача: адаптировать резюме под конкретную вакансию.",
        "",
        "Правила:",
        "1. Не добавляй опыт, которого нет в исходном резюме",
        "2. Переформулируй существующие пункты, используя язык вакансии",
        "3. Выдели наиболее релевантный опыт на первый план",
        "4. Используй ключевые слова из описания вакансии",
        "",
        "Вакансия: {vacancy['title']} в {vacancy['company']}",
        "Описание: {vacancy['description'][:500]}",
        "",
        "Резюме для адаптации:",
        "{base_resume}",
        "'''",
        "    response = await openai_client.chat.completions.create(",
        '        model="gpt-4o-mini",',
        "        messages=[{'role': 'user', 'content': prompt}],",
        "        max_tokens=1500,",
        "    )",
        "    return response.choices[0].message.content",
        "```",
        "",
        "Важный момент: используем `gpt-4o-mini` вместо `gpt-4`. "
        "Разница в качестве для этой задачи незначительная, разница в цене — в 15 раз.",
        "",
        "## Интеграция с hh.ru API",
        "",
        "hh.ru предоставляет полноценный REST API. Для отправки отклика нужен OAuth-токен пользователя:",
        "",
        "```python",
        "async def apply_to_vacancy(vacancy_id, resume_id, access_token, cover_letter=''):",
        "    async with aiohttp.ClientSession() as session:",
        "        async with session.post(",
        '            "https://api.hh.ru/negotiations",',
        "            headers={",
        '                "Authorization": f"Bearer {access_token}",',
        '                "HH-User-Agent": "ResumeAI/1.0 (support@resumeai.bot)",',
        "            },",
        "            json={",
        '                "vacancy_id": vacancy_id,',
        '                "resume_id": resume_id,',
        '                "message": cover_letter,',
        "            },",
        "        ) as resp:",
        "            if resp.status == 201:",
        "                return {'success': True}",
        "            return {'success': False, 'error': await resp.json()}",
        "```",
        "",
        "Лимиты hh.ru: не более 200 откликов в день с одного аккаунта. "
        "Мы ставим лимит 50/день по умолчанию — надёжнее и не привлекает внимания.",
        "",
        "## Мониторинг",
        "",
        "Health check запускается каждые 5 минут через systemd timer:",
        "",
        "```python",
        "async def main():",
        "    checks = [check_bot_db, check_autoapply_api, check_hh_api, check_disk_space]",
        "    results = await asyncio.gather(*[fn() for fn in checks])",
        "    failures = [msg for ok, msg in results if not ok]",
        "    if failures:",
        '        await send_telegram_alert("\\n".join(failures))',
        "        # попытка авторестарта упавших сервисов",
        "```",
        "",
        "При падении сервиса — автоматический `systemctl restart`, "
        "ожидание 30 секунд, повторная проверка. Если не восстановился — алерт в Telegram.",
        "",
        "## Стоимость эксплуатации",
        "",
        "| Компонент | Стоимость |",
        "|-----------|-----------|",
        "| VPS (2 CPU, 4GB RAM) | ~500 руб/мес |",
        "| OpenAI API (500 генераций/мес) | ~$10 |",
        "| hh.ru API | бесплатно |",
        "| SuperJob API | бесплатно |",
        "| Домен | ~900 руб/год |",
        "",
        "Итого: ~1400 руб/мес для полноценной работы.",
        "",
        "## Попробовать",
        "",
        "Бот доступен как @topbestworkerbot в Telegram. Бесплатный тариф: 3 автоотклика/день.",
        "Веб-версия: resumeai.bot",
        "",
        "Код написан на Python 3.11, aiogram 3, FastAPI. "
        "Если интересно — пишите вопросы в комментарии.",
        "",
    ]
    return "\n".join(lines)


def _vc_ru_article_ru() -> str:
    return (
        "# vc.ru — Статья о стартапе\n\n"
        "**Заголовок:** Мы автоматизировали поиск работы: 300 откликов в неделю, "
        "12 собеседований, 3 оффера\n\n"
        "**Раздел:** Стартапы, Карьера, ИИ\n\n"
        "---\n\n"
        "Идея родилась из личной боли: после сокращения пришлось тратить по 3-4 часа в день "
        "на рутину — редактировать резюме, писать сопроводительные письма, заполнять формы. "
        "При том что работа почти везде одна и та же.\n\n"
        "Мы решили это автоматизировать. Так появился РезюмеАИ.\n\n"
        "## Что делает продукт\n\n"
        "**РезюмеАИ** — это Telegram бот с двумя режимами:\n\n"
        "**1. AI Конструктор Резюме**\n"
        "Загружаете базовое резюме, вставляете ссылку на вакансию — через 30 секунд получаете "
        "PDF-резюме, адаптированное именно под эту должность. GPT-4 переписывает формулировки, "
        "расставляет нужные ключевые слова, выделяет релевантный опыт.\n\n"
        "**2. АвтоОтклик**\n"
        "Настраиваете фильтры (должность, зарплата, город, ключевые слова, чёрный список компаний) — "
        "бот сам ищет подходящие вакансии на hh.ru, SuperJob, LinkedIn и отправляет отклики "
        "с персонализированным резюме для каждой позиции.\n\n"
        "## Результаты первых пользователей\n\n"
        "Средняя статистика по пользователям на платном тарифе за первый месяц:\n"
        "- 200-300 откликов за 7 дней\n"
        "- 10-15% callback rate (против 2-3% при стандартной рассылке)\n"
        "- Среднее время до первого собеседования: 4 дня\n\n"
        "## Бизнес-модель\n\n"
        "**Бесплатно:** 3 автооткликов/день + 2 AI-резюме/день\n\n"
        "**Базовый** (499 руб/мес): 50 откликов/день, все источники вакансий\n\n"
        "**Профессиональный** (999 руб/мес): безлимит, LinkedIn автоматизация, приоритетная обработка\n\n"
        "**Карьерный** (2499 руб/мес): личный карьерный ассистент + анализ рынка + "
        "переговоры по зарплате (AI)\n\n"
        "## Технический стек\n\n"
        "Python + aiogram 3 + FastAPI + OpenAI API + Playwright + hh.ru API. "
        "Деплой на одном VPS, мониторинг через собственный health check скрипт с алертами в Telegram.\n\n"
        "Стоимость OpenAI на 500 генераций резюме в месяц: ~$10. Маржинальность высокая.\n\n"
        "## Планы\n\n"
        "- Интеграция с LinkedIn Jobs API\n"
        "- Анализ рынка: 'сколько платят за вашу должность в вашем городе'\n"
        "- Трекер отказов с аналитикой — почему не берут\n"
        "- B2B: рекрутинговые агентства как клиенты\n\n"
        "## Попробовать\n\n"
        "Telegram: @topbestworkerbot\n"
        "Сайт: resumeai.bot\n\n"
        "Бесплатный тариф без регистрации — просто запустите бота.\n"
    )


CONTENT = {
    "github_awesome_telegram_bots_PR.md": _github_awesome_telegram_bots_pr(),
    "github_awesome_ai_tools_PR.md":      _github_awesome_ai_tools_pr(),
    "reddit_post_EN.md":                   _reddit_post_en(),
    "reddit_post_RU.md":                   _reddit_post_ru(),
    "medium_article_EN.md":               _medium_article_en(),
    "devto_article_EN.md":                _devto_article_en(),
    "habr_article_RU.md":                 _habr_article_ru(),
    "vc_ru_article_RU.md":               _vc_ru_article_ru(),
}


def main():
    print("\n" + "=" * 55)
    print("  BACKLINK CONTENT GENERATOR — ResumeAI")
    print("=" * 55)

    for filename, content in CONTENT.items():
        out_path = OUTPUT_DIR / filename
        out_path.write_text(content, encoding="utf-8")
        word_count = len(content.split())
        print(f"  Wrote: {filename}")
        print(f"         {word_count} words | {out_path}")

    print(f"\n  Total files: {len(CONTENT)}")
    print(f"  Output dir:  {OUTPUT_DIR}/")
    print("\n" + "=" * 55)
    print("  POSTING GUIDE")
    print("=" * 55)
    guide = """
  github_awesome_telegram_bots_PR.md
    -> Find repos: github.com/search?q=awesome-telegram-bots
    -> Fork, add one line to README, open PR

  github_awesome_ai_tools_PR.md
    -> Find repos: github.com/search?q=awesome-ai-tools
    -> Fork, add one line to README, open PR

  reddit_post_EN.md
    -> Post to r/jobs, r/GetEmployed, r/cscareerquestions
    -> Wait 24h between posts to avoid spam filters

  reddit_post_RU.md
    -> Post to r/russia, ru-dev communities

  medium_article_EN.md
    -> medium.com/new-story — paste and publish
    -> Add canonical URL: resumeai.bot

  devto_article_EN.md
    -> dev.to/new — paste, tags: python, automation, openai

  habr_article_RU.md
    -> habr.com/ru/post/create/
    -> Хабы: Python, Карьера в IT, OpenAI

  vc_ru_article_RU.md
    -> vc.ru/write
    -> Раздел: Стартапы / Карьера
"""
    print(guide)


if __name__ == "__main__":
    main()
