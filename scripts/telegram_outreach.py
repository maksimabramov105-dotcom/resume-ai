#!/usr/bin/env python3
"""
scripts/telegram_outreach.py — Post helpful career advice to Telegram channels.

Usage:
    python scripts/telegram_outreach.py

Env vars:
    BOT_TOKEN              — Telegram bot token
    TG_OUTREACH_CHANNELS   — comma-separated channel IDs / @usernames
                             e.g. "@careerchat,@hrrussia,-1001234567890"
    OPENAI_API_KEY / OPENROUTER_API_KEY

Limits:
    - Max 3 channels per run
    - 1 post per channel per day (checked against data/tg_outreach_log.csv)
    - 30-second delay between posts

Posts end with soft CTA: "Больше советов: @topbestworkerbot"
"""
from __future__ import annotations

import csv
import logging
import os
import sys
import time
from datetime import date, datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [tg_outreach] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
LOG_CSV = os.path.join(DATA_DIR, "tg_outreach_log.csv")

MAX_CHANNELS = 3
DELAY_BETWEEN_POSTS = 30  # seconds
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_BASE_URL", "https://resumeai-bot.ru")

# ── Content generation ────────────────────────────────────────────────────────

_TOPICS_RU = [
    "Как написать цепляющий заголовок резюме",
    "Метод STAR на собеседовании — как отвечать на поведенческие вопросы",
    "Что такое ATS и почему 75% резюме отсеиваются автоматически",
    "Как за 5 минут улучшить резюме перед отправкой",
    "LinkedIn vs hh.ru: где искать работу эффективнее в 2026",
    "Топ-5 ошибок в сопроводительном письме",
    "Как получить оффер быстрее: план на первые 2 недели поиска",
]

_TOPICS_EN = [
    "How to write a compelling resume headline",
    "The STAR method in interviews — how to answer behavioral questions",
    "What is ATS and why 75% of resumes are auto-rejected",
    "How to improve your resume in 5 minutes before applying",
    "LinkedIn vs Indeed: where to job search smarter in 2026",
    "Top 5 mistakes in a cover letter",
    "How to get an offer faster: a plan for the first 2 weeks of job searching",
]


def _generate_post(topic: str, lang: str) -> str:
    """Use OpenRouter/OpenAI to generate a helpful post about the topic."""
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    cta = "Больше советов: @topbestworkerbot" if lang == "ru" else "More tips: @topbestworkerbot"

    if not api_key:
        logger.warning("No AI API key — using static fallback post")
        return _static_post(topic, lang, cta)

    try:
        import httpx
        if os.getenv("OPENROUTER_API_KEY"):
            base_url = "https://openrouter.ai/api/v1"
            model = "openai/gpt-4o-mini"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": WEBAPP_URL,
                "X-Title": "ResumeAI",
            }
        else:
            base_url = "https://api.openai.com/v1"
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            headers = {"Authorization": f"Bearer {api_key}"}

        if lang == "ru":
            prompt = (
                f"Напиши короткий и полезный пост для Telegram-канала о карьере на тему: «{topic}». "
                "2-4 конкретных совета. Эмодзи в начале каждого пункта. "
                "Никакой воды. Без хэштегов. "
                "Максимум 150 токенов."
            )
        else:
            prompt = (
                f"Write a short, useful Telegram post about careers on the topic: '{topic}'. "
                "2-4 concrete tips. Emoji at the start of each point. "
                "No fluff. No hashtags. "
                "Maximum 150 tokens."
            )

        payload = {
            "model": model,
            "max_tokens": 150,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = httpx.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text + f"\n\n{cta}"
    except Exception as exc:
        logger.warning("AI post generation failed (%s) — using fallback", exc)
        return _static_post(topic, lang, cta)


def _static_post(topic: str, lang: str, cta: str) -> str:
    if lang == "ru":
        return (
            f"💡 <b>{topic}</b>\n\n"
            "✅ Используйте конкретные цифры и результаты\n"
            "✅ Адаптируйте каждое резюме под конкретную вакансию\n"
            "✅ Проверьте ATS-совместимость перед отправкой\n\n"
            f"{cta}"
        )
    return (
        f"💡 <b>{topic}</b>\n\n"
        "✅ Use specific numbers and measurable results\n"
        "✅ Tailor each resume to the specific job posting\n"
        "✅ Check ATS compatibility before applying\n\n"
        f"{cta}"
    )


# ── Log helpers ───────────────────────────────────────────────────────────────

def _already_posted_today(channel: str) -> bool:
    today = str(date.today())
    if not os.path.exists(LOG_CSV):
        return False
    with open(LOG_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("date") == today and row.get("channel") == channel and row.get("status") == "sent":
                return True
    return False


def _log_post(channel: str, status: str, preview: str) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    is_new = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "channel", "status", "preview"])
        if is_new:
            writer.writeheader()
        writer.writerow({
            "date": str(date.today()),
            "channel": channel,
            "status": status,
            "preview": preview[:120],
        })


# ── Telegram send ─────────────────────────────────────────────────────────────

def _post_to_channel(channel: str, text: str) -> bool:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not set — cannot post to Telegram")
        return False
    try:
        import httpx
        resp = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": channel,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        data = resp.json()
        if data.get("ok"):
            logger.info("[tg] Posted to %s", channel)
            return True
        logger.error("[tg] Error posting to %s: %s", channel, data.get("description"))
        return False
    except Exception as exc:
        logger.error("[tg] Exception posting to %s: %s", channel, exc)
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def run_outreach() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    channels_raw = os.getenv("TG_OUTREACH_CHANNELS", "")
    if not channels_raw:
        logger.warning("TG_OUTREACH_CHANNELS not set — nothing to post to.")
        return

    channels = [c.strip() for c in channels_raw.split(",") if c.strip()][:MAX_CHANNELS]
    logger.info("Posting to %d channel(s): %s", len(channels), channels)

    # Pick today's topic by day-of-year rotation
    day_idx = datetime.utcnow().timetuple().tm_yday

    for channel in channels:
        if _already_posted_today(channel):
            logger.info("Already posted to %s today — skipping.", channel)
            continue

        # Detect language from channel name (very simple heuristic: channels with _en or -en → en)
        lang = "en" if channel.endswith(("_en", "-en")) else "ru"
        topics = _TOPICS_EN if lang == "en" else _TOPICS_RU
        topic = topics[day_idx % len(topics)]

        post_text = _generate_post(topic, lang)
        success = _post_to_channel(channel, post_text)
        _log_post(channel, "sent" if success else "error", post_text[:80])

        if success and channels.index(channel) < len(channels) - 1:
            time.sleep(DELAY_BETWEEN_POSTS)


if __name__ == "__main__":
    run_outreach()
