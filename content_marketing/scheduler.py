#!/usr/bin/env python3
"""
scheduler.py — Master content marketing scheduler.

Runs 24/7 on the VPS. Uses the `schedule` library for weekly jobs.
All jobs are wrapped in try/except with Telegram alerts on failure.

Weekly schedule (UTC):
  Monday    08:00 — Generate new content (content_generator.py)
  Tuesday   10:00 — Post to Reddit
  Wednesday 09:00 — Publish to Telegra.ph
  Thursday  11:00 — Post to VK
  Friday    10:00 — Post to Reddit (second post)
  Saturday  12:00 — Publish to Telegra.ph (second article)

Usage:
    python3 scheduler.py           # run continuously (production)
    python3 scheduler.py --once    # run all jobs immediately (testing)
"""

import logging
import sys
import time
import traceback
import urllib.parse
import urllib.request
from pathlib import Path

import schedule

sys.path.insert(0, str(Path(__file__).parent.parent))

from content_marketing.config import (
    BOT_TOKEN,
    MY_CHAT_ID,
    LOGS_DIR,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "master_scheduler_log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)


# ── Telegram alert ────────────────────────────────────────────────────────────

def send_telegram_alert(text: str) -> None:
    """Send a message to MY_CHAT_ID via the existing bot token."""
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN not set — cannot send Telegram alert")
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": MY_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        log.error("Failed to send Telegram alert: %s", e)


# ── Job wrapper ───────────────────────────────────────────────────────────────

def run_job(name: str, func):
    """
    Execute a job function with logging and error handling.
    Sends a Telegram alert if the job fails.
    """
    log.info("▶ Starting job: %s", name)
    try:
        func()
        log.info("✅ Job finished: %s", name)
        return True
    except Exception:
        tb = traceback.format_exc()
        log.error("❌ Job failed: %s\n%s", name, tb)
        send_telegram_alert(
            f"⚠️ <b>Content Marketing Alert</b>\n"
            f"Job <code>{name}</code> failed:\n"
            f"<pre>{tb[-800:]}</pre>"
        )
        return False


# ── Individual job functions ──────────────────────────────────────────────────

def job_generate_content():
    """Monday: generate one week's worth of content."""
    from content_marketing.content_generator import generate_for_topic, TOPICS
    import json
    from content_marketing.config import CONTENT_DIR

    # Find next topic that hasn't been generated
    from content_marketing.content_generator import slugify
    generated = {d.name.split("_", 1)[1] for d in CONTENT_DIR.iterdir()
                 if d.is_dir() and "_" in d.name}

    for topic in TOPICS:
        if slugify(topic) not in generated:
            log.info("Generating content for: %s", topic)
            generate_for_topic(topic)
            return

    # All topics done — cycle back to first
    log.info("All topics generated, cycling back to first topic")
    generate_for_topic(TOPICS[0])


def job_reddit_post():
    """Tuesday/Friday: post to Reddit."""
    from content_marketing.reddit_poster import main as reddit_main
    reddit_main(dry_run=False)


def job_telegraph_publish():
    """Wednesday/Saturday: publish to Telegra.ph."""
    from content_marketing.telegraph_publisher import main as telegraph_main
    telegraph_main(dry_run=False)


# ── Schedule setup ────────────────────────────────────────────────────────────

def setup_schedule():
    """Register all weekly jobs with the schedule library."""

    schedule.every().monday.at("08:00").do(
        run_job, "generate_content", job_generate_content
    )
    schedule.every().tuesday.at("10:00").do(
        run_job, "reddit_post_1", job_reddit_post
    )
    schedule.every().wednesday.at("09:00").do(
        run_job, "telegraph_publish_1", job_telegraph_publish
    )
    schedule.every().friday.at("10:00").do(
        run_job, "reddit_post_2", job_reddit_post
    )
    schedule.every().saturday.at("12:00").do(
        run_job, "telegraph_publish_2", job_telegraph_publish
    )

    log.info("Schedule configured:")
    for job in schedule.jobs:
        log.info("  %s", job)


def main():
    if "--once" in sys.argv:
        # Run all jobs immediately for testing
        log.info("Running all jobs once (--once mode)…")
        run_job("generate_content",    job_generate_content)
        run_job("reddit_post",         job_reddit_post)
        run_job("telegraph_publish",   job_telegraph_publish)
        log.info("All test runs complete.")
        return

    setup_schedule()
    log.info("Content marketing scheduler started. Press Ctrl+C to stop.")
    send_telegram_alert("📢 Content marketing scheduler started on VPS.")

    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            log.info("Scheduler stopped by user.")
            break
        except Exception as e:
            log.error("Scheduler loop error: %s", e)
            send_telegram_alert(f"⚠️ Scheduler loop error: {e}")
            time.sleep(300)  # Wait 5 min before resuming


if __name__ == "__main__":
    main()
