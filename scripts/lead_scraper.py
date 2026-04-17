#!/usr/bin/env python3
"""
scripts/lead_scraper.py — Daily lead-generation cron job.

What it does:
  1. Scrapes public job forums (Reddit) for "resume help" posts posted today
  2. Generates a personalized reply draft for each new post using AI
  3. Saves new leads to data/leads.csv (deduped by post URL)
  4. Saves reply drafts to data/drafts.csv
  5. Sends a Telegram digest to ADMIN_ID:
       "5 new leads found, drafts ready in data/drafts.csv"

Sources scraped:
  - Reddit (r/resumes, r/jobs, r/jobsearchhacks, r/cscareerquestions, r/ExperiencedDevs)
    via public JSON API — no API key required, just a User-Agent header.

Scheduling:
  Registered in marketing_cron.setup_marketing_scheduler() at 08:00 UTC daily.
  Standalone: python3 scripts/lead_scraper.py

Env vars used:
  BOT_TOKEN          — for Telegram digest
  ADMIN_ID           — Telegram user ID to receive digest
  OPENAI_API_KEY / OPENROUTER_API_KEY  — AI draft generation
  OPENAI_MODEL       — model name (default gpt-4o-mini)
  WEBAPP_BASE_URL    — link in drafts (default https://resumeai-bot.ru)
"""
from __future__ import annotations

import asyncio
import csv
import hashlib
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [lead_scraper] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

ROOT     = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
LEADS_CSV  = DATA_DIR / "leads.csv"
DRAFTS_CSV = DATA_DIR / "drafts.csv"

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
ADMIN_ID    = os.getenv("ADMIN_ID", "")
WEBAPP_URL  = os.getenv("WEBAPP_BASE_URL", "https://resumeai-bot.ru")
UTM_SUFFIX  = "?utm_source=reddit&utm_medium=organic&utm_campaign=lead_scraper"

# ── Reddit targets ────────────────────────────────────────────────────────────

REDDIT_TARGETS = [
    # (subreddit, search_query)
    ("resumes",              "review my resume"),
    ("resumes",              "help with resume"),
    ("jobs",                 "resume help"),
    ("jobs",                 "need resume feedback"),
    ("jobsearchhacks",       "resume"),
    ("cscareerquestions",    "resume help"),
    ("ExperiencedDevs",      "resume feedback"),
]

REDDIT_HEADERS = {
    "User-Agent": "ResumeAI-LeadBot/1.0 (contact: support@resumeai-bot.ru)",
    "Accept": "application/json",
}

MAX_POSTS_PER_QUERY = 10   # Reddit returns up to 25; we cap per query
MAX_POST_AGE_HOURS  = 48   # only posts from last 48h are considered "fresh"


# ── Reddit scraper ────────────────────────────────────────────────────────────

def _scrape_reddit_sync(subreddit: str, query: str) -> list[dict]:
    """Synchronous HTTP call to Reddit public JSON search API."""
    import urllib.request, urllib.parse, json

    params = urllib.parse.urlencode({
        "q": query,
        "sort": "new",
        "t": "day",
        "limit": MAX_POSTS_PER_QUERY,
        "restrict_sr": "true",
    })
    url = f"https://www.reddit.com/r/{subreddit}/search.json?{params}"

    try:
        req = urllib.request.Request(url, headers=REDDIT_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.warning("Reddit %s/%s fetch failed: %s", subreddit, query, exc)
        return []

    posts = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=MAX_POST_AGE_HOURS)

    for child in data.get("data", {}).get("children", []):
        p = child.get("data", {})
        # Skip deleted/removed posts
        if p.get("removed_by_category") or p.get("author") in ("[deleted]", "AutoModerator"):
            continue
        created_utc = p.get("created_utc", 0)
        post_dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        if post_dt < cutoff:
            continue

        posts.append({
            "url":       f"https://www.reddit.com{p.get('permalink', '')}",
            "title":     p.get("title", "")[:200],
            "body":      (p.get("selftext") or "")[:500],
            "author":    p.get("author", ""),
            "subreddit": subreddit,
            "created":   post_dt.strftime("%Y-%m-%d %H:%M UTC"),
            "score":     str(p.get("score", 0)),
        })

    logger.info("Reddit r/%s q=%r → %d fresh posts", subreddit, query, len(posts))
    return posts


def scrape_all_sources() -> list[dict]:
    """Scrape all Reddit targets and return deduped posts."""
    all_posts: dict[str, dict] = {}  # url → post

    for subreddit, query in REDDIT_TARGETS:
        time.sleep(1.5)  # be polite to Reddit
        posts = _scrape_reddit_sync(subreddit, query)
        for post in posts:
            if post["url"] not in all_posts:
                all_posts[post["url"]] = post

    return list(all_posts.values())


# ── Dedup against existing leads ──────────────────────────────────────────────

def _load_known_urls() -> set[str]:
    known: set[str] = set()
    for csv_path in (LEADS_CSV, DRAFTS_CSV):
        if not csv_path.exists():
            continue
        with csv_path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                url = row.get("url", "").strip()
                if url:
                    known.add(url)
    return known


def _append_leads(posts: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    is_new = not LEADS_CSV.exists()
    fields = ["url", "title", "author", "subreddit", "created", "score", "body"]
    with LEADS_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if is_new:
            w.writeheader()
        for p in posts:
            w.writerow(p)


# ── AI draft generation ───────────────────────────────────────────────────────

def _generate_draft_sync(post: dict) -> str:
    """Generate a helpful Reddit reply draft using AI."""
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    cta_url = f"{WEBAPP_URL}{UTM_SUFFIX}"
    tg_link = "https://t.me/topbestworkerbot"

    if not api_key:
        return _static_draft(post, cta_url, tg_link)

    try:
        import urllib.request, urllib.parse, json

        title  = post.get("title", "")
        body   = post.get("body", "")[:300]
        sub    = post.get("subreddit", "")

        system_prompt = (
            "You are a helpful career advisor replying to a Reddit post. "
            "Write a short, genuine, helpful reply (3-5 sentences). "
            "Give one concrete actionable tip based on their post. "
            "At the end, naturally mention ResumeAI as a free tool that might help "
            f"(link: {cta_url} or Telegram: @topbestworkerbot). "
            "Sound human, not salesy. No headers. No bullet points."
        )
        user_prompt = (
            f"Subreddit: r/{sub}\n"
            f"Post title: {title}\n"
            f"Post body: {body}\n\n"
            "Write a helpful reply:"
        )

        if os.getenv("OPENROUTER_API_KEY"):
            base_url = "https://openrouter.ai/api/v1"
            model    = "openai/gpt-4o-mini"
            extra_headers = {
                "HTTP-Referer": WEBAPP_URL,
                "X-Title": "ResumeAI Lead Scraper",
            }
        else:
            base_url = "https://api.openai.com/v1"
            model    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            extra_headers = {}

        payload = json.dumps({
            "model": model,
            "max_tokens": 200,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        }).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **extra_headers,
        }
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()

    except Exception as exc:
        logger.warning("Draft generation failed (%s) — using static template", exc)
        return _static_draft(post, cta_url, tg_link)


def _static_draft(post: dict, cta_url: str, tg_link: str) -> str:
    return (
        f"Great question! One thing that really helps is tailoring your resume "
        f"to the specific job description — ATS systems filter out 75% of resumes "
        f"before a human ever sees them.\n\n"
        f"You might find ResumeAI useful — it's free and creates an ATS-optimized "
        f"resume in 60 seconds: {cta_url} (also on Telegram: {tg_link})"
    )


def _append_drafts(posts: list[dict], drafts: list[str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    is_new = not DRAFTS_CSV.exists()
    fields = ["generated_at", "subreddit", "post_url", "post_title", "author", "draft_reply"]
    with DRAFTS_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if is_new:
            w.writeheader()
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        for post, draft in zip(posts, drafts):
            w.writerow({
                "generated_at": now,
                "subreddit":    post.get("subreddit", ""),
                "post_url":     post.get("url", ""),
                "post_title":   post.get("title", "")[:120],
                "author":       post.get("author", ""),
                "draft_reply":  draft.replace("\n", " ↩ "),  # flatten for CSV
            })


# ── Telegram digest ───────────────────────────────────────────────────────────

def _send_telegram_digest_sync(new_count: int, total_leads: int, sample: list[dict]) -> bool:
    """Send daily summary to admin."""
    if not BOT_TOKEN or not ADMIN_ID:
        logger.warning("BOT_TOKEN or ADMIN_ID not set — skipping Telegram digest")
        return False

    import urllib.request, urllib.parse, json

    sample_lines = ""
    for p in sample[:3]:
        sample_lines += f"\n  • r/{p['subreddit']}: {p['title'][:60]}…"

    text = (
        f"📋 <b>Ежедневный лид-дайджест</b>\n\n"
        f"🆕 <b>{new_count}</b> новых лидов найдено\n"
        f"📁 Всего лидов: <b>{total_leads}</b>\n"
        f"📝 Черновики ответов готовы в <code>data/drafts.csv</code>\n"
        f"\n<b>Примеры:</b>{sample_lines if sample_lines else ' нет новых'}\n\n"
        f"🔗 Запустите <code>python3 scripts/email_outreach.py</code> для рассылки"
    )

    try:
        payload = json.dumps({
            "chat_id": int(ADMIN_ID),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("ok"):
            logger.info("Telegram digest sent to admin %s", ADMIN_ID)
            return True
        logger.error("Telegram digest error: %s", data.get("description"))
        return False
    except Exception as exc:
        logger.error("Telegram digest exception: %s", exc)
        return False


# ── Count existing leads ──────────────────────────────────────────────────────

def _count_leads() -> int:
    if not LEADS_CSV.exists():
        return 0
    with LEADS_CSV.open(newline="", encoding="utf-8") as f:
        return max(0, sum(1 for _ in csv.DictReader(f)))


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_lead_scraper() -> None:
    """
    Async wrapper so APScheduler's AsyncIOScheduler can schedule this directly.
    All heavy work is synchronous (Reddit API + AI calls) — run in a thread
    to avoid blocking the event loop.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_sync)


def _run_sync() -> None:
    """The actual synchronous work."""
    logger.info("=== lead_scraper daily run ===")

    # 1. Scrape
    posts = scrape_all_sources()
    logger.info("Total posts scraped: %d", len(posts))

    # 2. Dedup
    known_urls = _load_known_urls()
    new_posts  = [p for p in posts if p["url"] not in known_urls]
    logger.info("New posts (not yet in CSV): %d", len(new_posts))

    # 3. Save leads
    if new_posts:
        _append_leads(new_posts)

    # 4. Generate drafts (with small delay to respect rate limits)
    drafts: list[str] = []
    for i, post in enumerate(new_posts):
        draft = _generate_draft_sync(post)
        drafts.append(draft)
        logger.info("Draft %d/%d generated for %s", i + 1, len(new_posts), post["url"])
        if i < len(new_posts) - 1:
            time.sleep(2)  # 2s between AI calls

    if new_posts:
        _append_drafts(new_posts, drafts)

    # 5. Telegram digest
    total = _count_leads()
    _send_telegram_digest_sync(len(new_posts), total, new_posts)

    logger.info(
        "Done. new_leads=%d, total_leads=%d, drafts_written=%d",
        len(new_posts), total, len(drafts),
    )


if __name__ == "__main__":
    _run_sync()
