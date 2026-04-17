#!/usr/bin/env python3
"""
scripts/email_outreach.py — Personalized cold-email outreach from a CSV of leads.

Usage:
    python scripts/email_outreach.py

CSV format (data/leads.csv) — header row required:
    email,name,language,role

Rate limits:
    - Max 50 emails / day (checks today's count in data/outreach_log.csv)
    - 10-second delay between sends

CAN-SPAM compliant:
    - Physical address placeholder in footer
    - Unsubscribe instruction in every email

Env vars (loaded from .env):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
    OPENAI_API_KEY  (or OPENROUTER_API_KEY for OpenRouter)
    OPENAI_MODEL    (default: gpt-4o-mini)
    WEBAPP_BASE_URL (default: https://resumeai-bot.ru)
"""
from __future__ import annotations

import csv
import logging
import os
import smtplib
import sys
import time
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Load .env if dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [email_outreach] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
LEADS_CSV = os.path.join(DATA_DIR, "leads.csv")
LOG_CSV = os.path.join(DATA_DIR, "outreach_log.csv")

WEBAPP_URL = os.getenv("WEBAPP_BASE_URL", "https://resumeai-bot.ru")
TG_BOT = "https://t.me/topbestworkerbot"

MAX_PER_DAY = 50
DELAY_BETWEEN_SENDS = 10  # seconds

# ── AI personalization ────────────────────────────────────────────────────────

def _generate_email_body(name: str, role: str, lang: str) -> str:
    """Use OpenRouter/OpenAI to generate a short personalized email body."""
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("No AI API key — using static template")
        return _static_template(name, role, lang)

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
                f"Напиши короткое, дружелюбное холодное письмо (не более 5 предложений) "
                f"для кандидата по имени {name}, ищущего работу {role}. "
                f"Упомяни, что ResumeAI создаёт ATS-оптимизированные резюме за 60 секунд бесплатно. "
                "Не включай тему письма, приветствие и подпись — только тело. "
                "Язык: русский."
            )
        else:
            prompt = (
                f"Write a short, friendly cold email (max 5 sentences) to a candidate named {name} "
                f"who is looking for {role} positions. "
                f"Mention that ResumeAI creates ATS-optimized resumes in 60 seconds for free. "
                "Do not include subject, greeting or signature — body only. "
                "Language: English."
            )

        payload = {
            "model": model,
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = httpx.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("AI generation failed (%s) — using static template", exc)
        return _static_template(name, role, lang)


def _static_template(name: str, role: str, lang: str) -> str:
    link = f"{WEBAPP_URL}?utm_source=email&utm_medium=outreach&utm_campaign=cold_email"
    if lang == "ru":
        return (
            f"Привет, {name}!\n\n"
            f"Вижу, вы ищете работу {role}. "
            "Наш AI создаёт ATS-оптимизированные резюме за 60 секунд — бесплатно и без регистрации.\n\n"
            f"Попробуйте прямо сейчас: {link}\n\n"
            "Или в Telegram: https://t.me/topbestworkerbot"
        )
    return (
        f"Hi {name},\n\n"
        f"I noticed you're looking for {role} positions. "
        "Our AI creates ATS-optimized resumes in 60 seconds — free, no signup required.\n\n"
        f"Try it now: {link}\n\n"
        "Or on Telegram: https://t.me/topbestworkerbot"
    )


# ── Email helpers ─────────────────────────────────────────────────────────────

def _build_email(to_email: str, name: str, role: str, lang: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["From"] = os.getenv("SMTP_FROM", "ResumeAI <noreply@resumeai-bot.ru>")
    msg["To"] = to_email

    if lang == "ru":
        msg["Subject"] = f"{name}, ATS-резюме за 60 секунд — бесплатно"
    else:
        msg["Subject"] = f"{name}, ATS-optimized resume in 60 seconds — free"

    body_text = _generate_email_body(name, role, lang)

    unsubscribe_footer = (
        "\n\n--\nResumeAI | resumeai-bot.ru | Moscow, Russia\n"
        "To unsubscribe reply with UNSUBSCRIBE or email support@resumeai-bot.ru\n"
    )
    if lang == "ru":
        unsubscribe_footer = (
            "\n\n--\nResumeAI | resumeai-bot.ru | Москва, Россия\n"
            "Чтобы отписаться, ответьте «ОТПИСАТЬСЯ» или напишите support@resumeai-bot.ru\n"
        )

    full_text = body_text + unsubscribe_footer

    # Plain text
    msg.attach(MIMEText(full_text, "plain", "utf-8"))

    # HTML version
    html_body = full_text.replace("\n", "<br>")
    html = f"""<!DOCTYPE html>
<html>
<body style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;color:#334155;">
  <p>{html_body}</p>
</body>
</html>"""
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg


def _send_email(msg: MIMEMultipart) -> None:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")

    with smtplib.SMTP(host, port, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


# ── Log helpers ───────────────────────────────────────────────────────────────

def _count_today_sends() -> int:
    today = str(date.today())
    if not os.path.exists(LOG_CSV):
        return 0
    count = 0
    with open(LOG_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("timestamp", "").startswith(today) and row.get("status") == "sent":
                count += 1
    return count


def _log_send(email: str, name: str, status: str, subject: str) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    is_new = not os.path.exists(LOG_CSV)
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "email", "name", "status", "subject"])
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.utcnow().isoformat(),
            "email": email,
            "name": name,
            "status": status,
            "subject": subject,
        })


# ── Main ──────────────────────────────────────────────────────────────────────

def run_outreach() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(LEADS_CSV):
        # Create a sample CSV
        with open(LEADS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["email", "name", "language", "role"])
            w.writerow(["example@email.com", "Иван", "ru", "Python Developer"])
        logger.info("Created sample %s — fill it in and re-run.", LEADS_CSV)
        return

    # Check SMTP config
    if not os.getenv("SMTP_USER"):
        logger.error("SMTP_USER not set — configure SMTP in .env before running.")
        return

    already_sent = _count_today_sends()
    if already_sent >= MAX_PER_DAY:
        logger.info("Daily limit reached (%d / %d). Try again tomorrow.", already_sent, MAX_PER_DAY)
        return

    # Load already-logged emails to avoid duplicates today
    sent_today: set[str] = set()
    today = str(date.today())
    if os.path.exists(LOG_CSV):
        with open(LOG_CSV, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("timestamp", "").startswith(today):
                    sent_today.add(row.get("email", ""))

    with open(LEADS_CSV, newline="", encoding="utf-8") as f:
        leads = list(csv.DictReader(f))

    sent_count = already_sent
    for lead in leads:
        if sent_count >= MAX_PER_DAY:
            logger.info("Daily limit %d reached — stopping.", MAX_PER_DAY)
            break

        email = lead.get("email", "").strip()
        name = lead.get("name", "").strip() or "друг"
        lang = lead.get("language", "ru").strip().lower()
        role = lead.get("role", "").strip() or ("специалист" if lang == "ru" else "specialist")

        if not email or "@" not in email:
            logger.warning("Skipping invalid email: %s", email)
            continue

        if email in sent_today:
            logger.info("Already sent to %s today — skipping.", email)
            continue

        try:
            msg = _build_email(email, name, role, lang)
            subject = msg["Subject"]
            _send_email(msg)
            _log_send(email, name, "sent", subject)
            logger.info("Sent to %s (%s)", email, name)
            sent_count += 1
            time.sleep(DELAY_BETWEEN_SENDS)
        except Exception as exc:
            logger.error("Failed to send to %s: %s", email, exc)
            _log_send(email, name, f"error:{exc}", "")


if __name__ == "__main__":
    run_outreach()
