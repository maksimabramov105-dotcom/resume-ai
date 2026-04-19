#!/usr/bin/env python3
"""
email_drip_cron.py — Runs daily at 10:00 UTC.
Sends the right drip email to each user based on days since signup.
"""
import os
import smtplib
import sqlite3
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST  = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT  = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER  = os.getenv("SMTP_USER", "")
SMTP_PASS  = os.getenv("SMTP_PASSWORD", os.getenv("SMTP_PASS", ""))
FROM_EMAIL = os.getenv("SMTP_FROM", os.getenv("FROM_EMAIL", "hello@resumeai-bot.ru"))
DB_PATH    = os.getenv("BOT_DB", os.getenv("DB_PATH", "/opt/resumeaibot/bot.db"))

DRIP_SEQUENCE = [
    (0, "Welcome to ResumeAI — here's your first step", """
<p>Hey! You just joined ResumeAI Bot. Here's what to do right now:</p>
<p><strong>Step 1:</strong> Send your resume to the bot (PDF or Word).<br>
<strong>Step 2:</strong> Set your job preferences (role, location, salary).<br>
<strong>Step 3:</strong> Hit "Start applying" — the bot does the rest.</p>
<p><a href="https://t.me/topbestworkerbot">Open the bot →</a></p>
<p>Questions? Just reply to this email.</p>
"""),
    (1, "Did you try it yet?", """
<p>You signed up yesterday but haven't sent your first application yet.</p>
<p>It takes 3 minutes to set up. Most people send their first 10 applications within an hour of setup.</p>
<p><a href="https://t.me/topbestworkerbot">Try it now →</a></p>
"""),
    (3, "The #1 reason resumes get rejected (before a human reads them)", """
<p>75% of resumes are rejected by ATS software before a recruiter sees them.</p>
<p>The fix: keyword matching. ATS systems scan for exact phrases from the job description.</p>
<p>ResumeAI does this automatically — it rewrites your resume summary for each job before applying.</p>
<p><a href="https://t.me/topbestworkerbot">See it in action →</a></p>
"""),
    (5, "Alex got 3 interviews in his first week. Here's what he did.", """
<p>Alex (software engineer, 6 months unemployed) set ResumeAI to apply to 30 jobs/day.</p>
<p>Day 1: 30 applications sent.<br>Day 3: First recruiter call.<br>Day 7: 3 phone screens booked.</p>
<p>He didn't change his resume. He just increased his volume and let the bot handle the repetitive part.</p>
<p><a href="https://t.me/topbestworkerbot">Start your streak →</a></p>
"""),
    (7, "Your free tier is running out", """
<p>You've been using ResumeAI for a week. On the free plan, you're limited to 3 applications/day.</p>
<p>Pro users send 50/day. At that volume, most people book their first interview within 2 weeks.</p>
<p><strong>Upgrade for $19.99/month</strong> — less than one day of job searching at a recruiter's rate.</p>
<p>Or start with our $2.99 trial — 30 applications in 14 days.</p>
<p><a href="https://t.me/topbestworkerbot">Upgrade now →</a></p>
"""),
    (14, "Quick question", """
<p>You've been with ResumeAI for 2 weeks. I want to make sure it's working for you.</p>
<p>Which best describes where you are?</p>
<p>
  A) Got interviews, things are going well<br>
  B) Got some responses, still looking<br>
  C) Not much happening yet<br>
  D) Haven't set it up yet
</p>
<p>Reply with A, B, C, or D — I read every reply personally.</p>
"""),
    (21, "Last thing I want to tell you", """
<p>Most job seekers give up after 2-3 weeks of silence. Don't.</p>
<p>The average job search takes 5-6 months at normal application volume.</p>
<p>At 50 applications/day with ResumeAI, you compress that into 3-4 weeks.</p>
<p>Use code <strong>KEEP50</strong> for 50% off your first month if you haven't upgraded.</p>
<p><a href="https://t.me/topbestworkerbot">Upgrade with KEEP50 →</a></p>
"""),
]


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drip_sent (
            user_id  INTEGER,
            day_index INTEGER,
            sent_at  TEXT,
            PRIMARY KEY (user_id, day_index)
        )
    """)
    # Add email column to users if missing
    try:
        conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()


def _get_users_to_email(conn: sqlite3.Connection) -> list[tuple]:
    today = datetime.utcnow().date()
    users = []
    for days, subject, body in DRIP_SEQUENCE:
        target_date = today - timedelta(days=days)
        rows = conn.execute(
            """
            SELECT user_id, email FROM users
            WHERE email IS NOT NULL AND email != ''
            AND DATE(created_at) = ?
            AND user_id NOT IN (
                SELECT user_id FROM drip_sent WHERE day_index = ?
            )
            """,
            (target_date.isoformat(), days),
        ).fetchall()
        for row in rows:
            users.append((row[0], row[1], days, subject, body))
    return users


def _send_email(to_email: str, subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = FROM_EMAIL
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


def _mark_sent(conn: sqlite3.Connection, user_id: int, day_index: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO drip_sent (user_id, day_index, sent_at) VALUES (?, ?, ?)",
        (user_id, day_index, datetime.utcnow().isoformat()),
    )
    conn.commit()


def main() -> None:
    if not SMTP_USER or not SMTP_PASS:
        print("[email_drip] SMTP not configured — skipping")
        return
    conn = sqlite3.connect(DB_PATH)
    _ensure_tables(conn)
    users = _get_users_to_email(conn)
    sent = 0
    for user_id, email, day_index, subject, body in users:
        try:
            _send_email(email, subject, body)
            _mark_sent(conn, user_id, day_index)
            sent += 1
            print(f"[email_drip] Sent day-{day_index} to {email}")
        except Exception as e:
            print(f"[email_drip] Failed {email}: {e}")
    conn.close()
    print(f"[email_drip] Done. Sent {sent} emails.")


if __name__ == "__main__":
    main()
