#!/usr/bin/env python3
"""
scripts/reddit_outreach.py — Post AI-generated replies to Reddit leads.

Reads draft replies from data/drafts.csv (produced by lead_scraper.py) and
posts each one as a comment on the corresponding Reddit thread.

Setup (one-time):
  1. Go to https://www.reddit.com/prefs/apps
  2. Click "create another app" at the bottom
  3. Choose "script", name it "ResumeAI Outreach", redirect URI: http://localhost:8080
  4. Note the client_id (under the app name) and client_secret
  5. Add to .env:
       REDDIT_USERNAME=your_username
       REDDIT_PASSWORD=your_password
       REDDIT_CLIENT_ID=xxxxxxxxxxxxxxx
       REDDIT_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxx

Usage:
    python3 scripts/reddit_outreach.py              # post up to MAX_PER_RUN new drafts
    python3 scripts/reddit_outreach.py --dry-run    # preview without posting
    python3 scripts/reddit_outreach.py --all        # include older drafts (not just today's)

Env vars:
    REDDIT_USERNAME, REDDIT_PASSWORD
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
    MAX_REDDIT_PER_RUN  — cap per execution (default: 10)
    MAX_REDDIT_PER_DAY  — daily safety cap (default: 15)

Logs every action to data/reddit_outreach_log.csv.
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
from datetime import datetime, date, timezone, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [reddit_outreach] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parents[1]
DATA_DIR  = ROOT / "data"
DRAFTS_CSV = DATA_DIR / "drafts.csv"
LOG_CSV    = DATA_DIR / "reddit_outreach_log.csv"

MAX_PER_RUN  = int(os.getenv("MAX_REDDIT_PER_RUN", "10"))
MAX_PER_DAY  = int(os.getenv("MAX_REDDIT_PER_DAY", "15"))
DELAY_SECS   = 45        # Reddit allows ~1 comment/min; 45s is safe
MAX_POST_AGE = 7         # skip threads older than this many days (likely archived)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _restore_newlines(text: str) -> str:
    """Drafts store newlines as ' ↩ ' or ' ↩  ↩ ' — restore them."""
    return text.replace(" ↩  ↩ ", "\n\n").replace(" ↩ ", "\n")


def _load_posted_urls() -> set[str]:
    """Return the set of Reddit URLs we've already commented on."""
    posted: set[str] = set()
    if not LOG_CSV.exists():
        return posted
    with LOG_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status") == "posted":
                posted.add(row.get("post_url", "").strip())
    return posted


def _count_today_posts() -> int:
    today = str(date.today())
    if not LOG_CSV.exists():
        return 0
    count = 0
    with LOG_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("date", "").startswith(today) and row.get("status") == "posted":
                count += 1
    return count


def _log(post_url: str, subreddit: str, post_title: str,
         status: str, note: str = "") -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    is_new = not LOG_CSV.exists()
    fields = ["date", "post_url", "subreddit", "post_title", "status", "note"]
    with LOG_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if is_new:
            w.writeheader()
        w.writerow({
            "date":       datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "post_url":   post_url,
            "subreddit":  subreddit,
            "post_title": post_title[:100],
            "status":     status,
            "note":       note[:200],
        })


def _is_too_old(generated_at: str) -> bool:
    """Return True if the draft is older than MAX_POST_AGE days."""
    try:
        dt = datetime.strptime(generated_at.strip(), "%Y-%m-%d %H:%M UTC")
        age = datetime.utcnow() - dt
        return age.days > MAX_POST_AGE
    except Exception:
        return False  # if we can't parse, don't skip


def _load_drafts(include_old: bool = False) -> list[dict]:
    if not DRAFTS_CSV.exists():
        logger.error("drafts.csv not found at %s", DRAFTS_CSV)
        return []
    with DRAFTS_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not include_old:
        rows = [r for r in rows if not _is_too_old(r.get("generated_at", ""))]
    return rows


# ── Reddit client ──────────────────────────────────────────────────────────────

def _get_reddit():
    """Build and return an authenticated praw.Reddit instance."""
    try:
        import praw
    except ImportError:
        logger.error("praw not installed. Run: pip install praw")
        sys.exit(1)

    username      = os.getenv("REDDIT_USERNAME", "").strip()
    password      = os.getenv("REDDIT_PASSWORD", "").strip()
    client_id     = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()

    missing = [k for k, v in {
        "REDDIT_USERNAME": username,
        "REDDIT_PASSWORD": password,
        "REDDIT_CLIENT_ID": client_id,
        "REDDIT_CLIENT_SECRET": client_secret,
    }.items() if not v]

    if missing:
        logger.error(
            "Missing env vars: %s\n"
            "Set them in .env — see script header for setup instructions.",
            ", ".join(missing),
        )
        sys.exit(1)

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent=f"ResumeAI:reddit_outreach:v1.0 (by /u/{username})",
    )
    # Verify auth
    try:
        me = reddit.user.me()
        logger.info("Authenticated as u/%s (karma: %s)", me.name, me.comment_karma)
    except Exception as exc:
        logger.error("Reddit auth failed: %s", exc)
        sys.exit(1)

    return reddit


# ── Posting ────────────────────────────────────────────────────────────────────

def _post_comment(reddit, post_url: str, reply_text: str, dry_run: bool) -> tuple[bool, str]:
    """
    Fetch the Reddit submission and post a top-level comment.
    Returns (success: bool, note: str).
    """
    if dry_run:
        logger.info("[DRY-RUN] Would post to %s", post_url)
        logger.info("[DRY-RUN] Reply:\n%s", reply_text[:200])
        return True, "dry_run"

    try:
        import praw.exceptions

        submission = reddit.submission(url=post_url)

        # Guard: skip if thread is locked or archived
        if submission.locked:
            return False, "thread_locked"
        if submission.archived:
            return False, "thread_archived"

        comment = submission.reply(reply_text)
        logger.info("Posted comment %s on %s", comment.id, post_url)
        return True, f"comment_id:{comment.id}"

    except Exception as exc:
        err = str(exc)
        logger.warning("Failed to post on %s: %s", post_url, err)
        return False, err[:200]


# ── Main ───────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False, include_old: bool = False) -> None:
    logger.info("=== reddit_outreach start (dry_run=%s, include_old=%s) ===",
                dry_run, include_old)

    # Check daily cap
    today_count = _count_today_posts()
    if today_count >= MAX_PER_DAY:
        logger.info("Daily cap reached (%d / %d). Try again tomorrow.",
                    today_count, MAX_PER_DAY)
        return

    reddit      = _get_reddit()
    posted_urls = _load_posted_urls()
    drafts      = _load_drafts(include_old=include_old)

    # Filter to unseen drafts
    pending = [d for d in drafts if d.get("post_url", "").strip() not in posted_urls]
    logger.info("Pending drafts: %d (already posted: %d, total in CSV: %d)",
                len(pending), len(posted_urls), len(drafts))

    if not pending:
        logger.info("Nothing new to post. All leads already replied to.")
        return

    # Cap to remaining quota
    remaining_today = MAX_PER_DAY - today_count
    batch = pending[: min(MAX_PER_RUN, remaining_today)]
    logger.info("Will post %d comment(s) this run.", len(batch))

    success_count = 0
    for i, draft in enumerate(batch):
        post_url  = draft.get("post_url", "").strip()
        subreddit = draft.get("subreddit", "")
        title     = draft.get("post_title", "")
        raw_reply = draft.get("draft_reply", "")
        reply     = _restore_newlines(raw_reply).strip()

        if not post_url or not reply:
            logger.warning("Skipping row with missing url or reply: %s", draft)
            continue

        logger.info("[%d/%d] Posting to r/%s — %s", i + 1, len(batch), subreddit, title[:60])

        ok, note = _post_comment(reddit, post_url, reply, dry_run)

        status = "posted" if ok else "failed"
        _log(post_url, subreddit, title, status, note)

        if ok:
            success_count += 1
        else:
            logger.warning("Skipped (reason: %s)", note)

        # Rate-limit pause between posts (skip after last one)
        if i < len(batch) - 1 and not dry_run:
            logger.info("Waiting %ds before next post…", DELAY_SECS)
            time.sleep(DELAY_SECS)

    logger.info(
        "Done. posted=%d / attempted=%d | today total: %d",
        success_count, len(batch), today_count + success_count,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post Reddit reply drafts")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Print what would be posted without actually posting")
    parser.add_argument("--all",      action="store_true",
                        help="Include drafts older than 7 days")
    args = parser.parse_args()
    run(dry_run=args.dry_run, include_old=args.all)
