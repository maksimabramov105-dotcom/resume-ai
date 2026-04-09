# Dev.to Article

**Title:** I Built a Job Application Bot With Python, FastAPI, and GPT-4 — Here's the Architecture

**Tags:** python, automation, openai, telegrambot

---

After getting laid off, I built a system to automate my job search. It ended with 12 interviews in 7 days. This post covers the technical architecture.

## Stack

- **Python 3.11** — main language
- **aiogram 3** — Telegram bot framework (async, excellent)
- **FastAPI** — REST API for the web dashboard
- **OpenAI API (GPT-4)** — resume tailoring
- **Playwright** — browser automation for sites without APIs
- **reportlab** — PDF generation
- **SQLite + aiosqlite** — storage (simple, works fine at this scale)
- **systemd** — process management on VPS

## The Resume Tailoring Prompt

The core of the system is a single well-engineered prompt:

```python
TAILORING_PROMPT = ("""
    You are an expert resume writer. Given a base resume and a job description:
    1. Identify the top 5-7 skills/requirements in the job description
    2. Rewrite the resume's experience bullets to use the same language and keywords
    3. Do NOT add experience that doesn't exist in the base resume
    4. Keep the same factual content — only rephrase and reorder
    5. Prioritize the most relevant experience first
    6. Output only the final resume text, no commentary

    Base Resume: {resume}
    Job Description: {job_description}
""")
```

The key constraint is 'do not add experience that doesn't exist.' This keeps it honest while dramatically improving keyword matching.

## hh.ru API Integration

hh.ru (Russia's largest job board) has a solid REST API:

```python
async def search_vacancies(query, area='1', per_page=20, salary_from=None):
    params = {
        "text": query,
        "area": area,
        "per_page": per_page,
        "order_by": "publication_time",
    }
    if salary_from:
        params["salary"] = salary_from
        params["only_with_salary"] = "true"
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.hh.ru/vacancies", params=params) as resp:
            data = await resp.json()
            return data.get("items", [])
```

Applying requires OAuth but the API is well-documented and the rate limits are reasonable.

## PDF Generation

reportlab for clean single-page PDFs:

```python
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

def generate_pdf(text, name, output_path):
    doc = SimpleDocTemplate(output_path)
    styles = getSampleStyleSheet()
    story = [Paragraph(name, styles['Title']), Spacer(1, 12)]
    for line in text.split('\n'):
        if line.strip():
            story.append(Paragraph(line, styles['Normal']))
    doc.build(story)
```

## Health Monitoring

Every 5 minutes, a systemd timer runs a health check that verifies:
- Both SQLite databases respond
- FastAPI is up on port 8080
- hh.ru API is reachable
- Disk space > 1GB
- All systemd services active

On failure: auto-restart attempt, then Telegram alert to admin.

## What I Learned

1. **Async everything** — the bot handles concurrent users, aiohttp + aiosqlite are essential
2. **Idempotency matters** — track applied vacancies to avoid duplicates
3. **Rate limit respect** — hh.ru will block you if you hammer their API. 1-2 req/sec is safe.
4. **Playwright is slow** — use native APIs where possible, browser automation only as fallback

## Try It

The bot is live at [@topbestworkerbot](https://t.me/topbestworkerbot). Web dashboard at [resumeai.bot](https://resumeai.bot).

Questions about the implementation? Drop them in the comments.
