#!/usr/bin/env python3
"""
Email drip cron — runs daily at 10:00 UTC.
Sends the right drip email to each user based on days since signup.
"""
import sqlite3
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

# Config — set these in environment variables
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS') or os.getenv('SMTP_PASSWORD', '')
FROM_EMAIL = os.getenv('FROM_EMAIL') or os.getenv('SMTP_FROM', 'hello@resumeai-bot.ru')
DB_PATH = os.getenv('DB_PATH', 'bot.db')

DRIP_SEQUENCE = [
    # (day, subject, html_body)
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
<p>You've been using ResumeAI for a week. On the free plan, you're limited to 10 applications/day.</p>
<p>Pro users send 50/day. At that volume, most people book their first interview within 2 weeks.</p>
<p><strong>Upgrade for $19.99/month</strong> — less than one day of job searching at a recruiter's rate.</p>
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


def get_users_to_email(conn):
    """Get users who need a drip email today."""
    cursor = conn.cursor()
    today = datetime.utcnow().date()
    users = []
    for days, subject, body in DRIP_SEQUENCE:
        target_date = today - timedelta(days=days)
        cursor.execute("""
            SELECT telegram_id, email FROM users
            WHERE email IS NOT NULL
            AND email != ''
            AND DATE(created_at) = ?
            AND telegram_id NOT IN (
                SELECT telegram_id FROM drip_sent WHERE day_index = ?
            )
        """, (target_date.isoformat(), days))
        for row in cursor.fetchall():
            users.append((row[0], row[1], days, subject, body))
    return users


def send_email(to_email, subject, html_body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)


def mark_sent(conn, telegram_id, day_index):
    conn.execute("""
        INSERT OR IGNORE INTO drip_sent (telegram_id, day_index, sent_at)
        VALUES (?, ?, ?)
    """, (telegram_id, day_index, datetime.utcnow().isoformat()))
    conn.commit()


def ensure_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drip_sent (
            telegram_id INTEGER,
            day_index INTEGER,
            sent_at TEXT,
            PRIMARY KEY (telegram_id, day_index)
        )
    """)
    conn.commit()


def main():
    conn = sqlite3.connect(DB_PATH)
    ensure_tables(conn)
    users_to_email = get_users_to_email(conn)
    sent = 0
    for telegram_id, email, day_index, subject, body in users_to_email:
        try:
            send_email(email, subject, body)
            mark_sent(conn, telegram_id, day_index)
            sent += 1
            print(f"Sent day-{day_index} email to {email}")
        except Exception as e:
            print(f"Failed to send to {email}: {e}")
    conn.close()
    print(f"Drip cron done. Sent {sent} emails.")


if __name__ == '__main__':
    main()
