#!/usr/bin/env python3
"""
reddit_poster.py — Automated Reddit posting for ResumeAI content marketing.

Posts generated Reddit content to targeted career subreddits.
Tracks what's been posted in posted_log.json to never repost.
Rotates subreddits, respects rate limits, logs everything.

Usage:
    python3 reddit_poster.py           # post next unposted piece
    python3 reddit_poster.py --dry-run # preview without posting
"""

import json
import logging
import random
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from content_marketing.config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USERNAME,
    REDDIT_PASSWORD,
    REDDIT_USER_AGENT,
    CONTENT_DIR,
    LOGS_DIR,
    BOT_LINK,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "reddit_log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Target subreddits (ordered by audience relevance) ────────────────────────
SUBREDDITS = [
    "resumes",
    "cscareerquestions",
    "careerguidance",
    "jobs",
    "GetEmployed",
    "jobsearchhacks",
    "digitalnomad",
    "Entrepreneur",
    "SideProject",
    "artificial",
]

# Subreddits that require a flair — map subreddit → preferred flair keyword
# PRAW will search for a flair containing this word (case-insensitive)
FLAIR_HINTS = {
    "resumes": "advice",
    "cscareerquestions": "general",
    "careerguidance": "advice",
}

POSTED_LOG = LOGS_DIR / "reddit_posted_log.json"


def load_posted_log() -> dict:
    """Load the record of previously posted content."""
    if POSTED_LOG.exists():
        return json.loads(POSTED_LOG.read_text(encoding="utf-8"))
    return {}


def save_posted_log(data: dict) -> None:
    POSTED_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_next_content() -> tuple[str, str, str] | None:
    """
    Find the oldest unposted reddit.txt in content_output/.
    Returns (folder_name, title, body) or None if nothing left.
    """
    posted = load_posted_log()
    already_posted = set(posted.keys())

    # Sort by folder date (oldest first) so we post in order
    folders = sorted(
        [d for d in CONTENT_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name
    )

    for folder in folders:
        reddit_file = folder / "reddit.txt"
        if not reddit_file.exists():
            continue
        if folder.name in already_posted:
            continue

        content = reddit_file.read_text(encoding="utf-8")

        # Parse TITLE: and BODY: from the generated content
        title = ""
        body_lines = []
        in_body = False

        for line in content.splitlines():
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.strip() == "BODY:":
                in_body = True
            elif in_body:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        if not title or not body:
            log.warning("Could not parse title/body from %s — skipping", folder.name)
            continue

        return folder.name, title, body

    return None


def pick_subreddit(posted: dict) -> str:
    """
    Pick the next subreddit to post to, rotating through the list.
    Avoids posting to the same subreddit twice in a row.
    """
    if not posted:
        return SUBREDDITS[0]

    # Find last used subreddit
    last_entry = max(posted.values(), key=lambda e: e.get("posted_at", ""), default=None)
    last_sub = last_entry.get("subreddit", "") if last_entry else ""

    # Rotate: pick next in list after last used
    try:
        idx = SUBREDDITS.index(last_sub)
        return SUBREDDITS[(idx + 1) % len(SUBREDDITS)]
    except ValueError:
        return SUBREDDITS[0]


def get_flair_id(subreddit, hint: str):
    """Find a post flair ID matching the hint string. Returns None if not found."""
    try:
        for flair in subreddit.flair.link_templates:
            if hint.lower() in flair.get("text", "").lower():
                return flair["id"]
    except Exception:
        pass
    return None


def post_to_reddit(title: str, body: str, subreddit_name: str, dry_run: bool = False) -> str | None:
    """
    Submit a self-post to the given subreddit.
    Returns the post URL on success, None on failure.
    """
    try:
        import praw
    except ImportError:
        log.error("praw not installed — run: pip install praw")
        return None

    if dry_run:
        log.info("[DRY RUN] Would post to r/%s:\nTITLE: %s\n---\n%s", subreddit_name, title, body[:200])
        return "https://reddit.com/r/dry_run/fake_post"

    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        username=REDDIT_USERNAME,
        password=REDDIT_PASSWORD,
        user_agent=REDDIT_USER_AGENT,
    )

    subreddit = reddit.subreddit(subreddit_name)

    # Try to set flair if the subreddit wants it
    flair_id = None
    if subreddit_name in FLAIR_HINTS:
        flair_id = get_flair_id(subreddit, FLAIR_HINTS[subreddit_name])

    kwargs = {"title": title, "selftext": body}
    if flair_id:
        kwargs["flair_id"] = flair_id

    submission = subreddit.submit(**kwargs)
    url = f"https://reddit.com{submission.permalink}"
    log.info("Posted to r/%s: %s", subreddit_name, url)
    return url


def main(dry_run: bool = False):
    # Validate credentials
    missing = [k for k in ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD"]
               if not globals().get(k) and not (k == "REDDIT_CLIENT_ID" and REDDIT_CLIENT_ID)]
    # Re-check from config module
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET or not REDDIT_USERNAME or not REDDIT_PASSWORD:
        log.error("Reddit credentials not configured. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD in .env")
        sys.exit(1)

    posted = load_posted_log()

    # Find next unposted content
    result = get_next_content()
    if not result:
        log.info("No unposted content found. Run content_generator.py first.")
        return

    folder_name, title, body = result
    subreddit_name = pick_subreddit(posted)

    log.info("Posting: '%s' → r/%s", title[:60], subreddit_name)

    # Random human-like delay (45–90 min converted to seconds for production,
    # kept at 2s here so the script doesn't block the scheduler for an hour)
    delay = random.randint(2, 5)
    log.info("Waiting %ds before posting…", delay)
    time.sleep(delay)

    for attempt in range(2):
        url = post_to_reddit(title, body, subreddit_name, dry_run=dry_run)
        if url:
            # Record the post
            posted[folder_name] = {
                "subreddit": subreddit_name,
                "title": title[:80],
                "url": url,
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }
            save_posted_log(posted)
            log.info("✅ Success: %s", url)
            return
        elif attempt == 0:
            log.warning("Post failed, retrying in 1 hour…")
            time.sleep(3600)

    log.error("❌ Failed to post after 2 attempts")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
