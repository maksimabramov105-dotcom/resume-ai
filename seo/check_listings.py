#!/usr/bin/env python3
"""
check_listings.py — Check if @topbestworkerbot appears in bot directories.

- Loads submission date from seo/submissions_log.txt
- Checks each directory via HTTP GET
- Tracks article posting status from seo/posted_articles.json
- Prints clean status report
- Saves report to seo/listings_status_YYYY-MM-DD.txt
- Sends Telegram summary to ADMIN_CHAT_ID

Usage:
  python3 seo/check_listings.py
"""

import os
import re
import json
import datetime
from pathlib import Path

import requests

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN     = os.getenv("BOT_TOKEN", "8442677408:AAFGf_Y14ZZntTVipyA5VQgeGNFenpJ_iQk")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "6246429438")

BOT_USERNAME  = "topbestworkerbot"
BOT_LINK      = f"https://t.me/{BOT_USERNAME}"

SEO_DIR          = Path(__file__).parent
LOG_FILE         = SEO_DIR / "submissions_log.txt"
ARTICLES_FILE    = SEO_DIR / "posted_articles.json"
TODAY            = datetime.date.today()
REPORT_FILE      = SEO_DIR / f"listings_status_{TODAY.isoformat()}.txt"

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_submission_date() -> datetime.date | None:
    """Read first submission date from submissions_log.txt."""
    if not LOG_FILE.exists():
        return None
    try:
        text = LOG_FILE.read_text(encoding="utf-8")
        # Lines look like: [HH:MM:SS] ... or [YYYY-MM-DD HH:MM:SS] ...
        # Look for date pattern in log
        m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if m:
            return datetime.date.fromisoformat(m.group(1))
    except Exception:
        pass
    return None


def days_since(d: datetime.date | None) -> str:
    if d is None:
        return "unknown"
    delta = (TODAY - d).days
    return f"{delta} day{'s' if delta != 1 else ''} ago"


def load_articles() -> dict:
    """Load posted_articles.json, create if missing."""
    if not ARTICLES_FILE.exists():
        template = {
            "vc.ru": {"posted": False, "url": "", "date": ""},
            "habr.com": {"posted": False, "url": "", "date": ""},
            "dtf.ru": {"posted": False, "url": "", "date": ""},
            "reddit_telegrambots": {"posted": False, "url": "", "date": ""},
            "reddit_resumes": {"posted": False, "url": "", "date": ""},
            "dev.to": {"posted": False, "url": "", "date": ""},
            "medium.com": {"posted": False, "url": "", "date": ""},
            "indiehackers.com": {"posted": False, "url": "", "date": ""},
        }
        ARTICLES_FILE.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
        return template
    try:
        return json.loads(ARTICLES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def check_url(url: str, keyword: str = BOT_USERNAME) -> bool:
    """Return True if URL returns 200 and keyword is in body."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if r.status_code == 200 and keyword.lower() in r.text.lower():
            return True
        return False
    except Exception:
        return False


def check_url_status(url: str) -> int:
    """Return HTTP status code, 0 on error."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        return r.status_code
    except Exception:
        return 0


def tg_send(chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=15)
        return r.status_code == 200
    except Exception:
        return False


# ── Directory checks ──────────────────────────────────────────────────────────

DIRECTORIES = [
    {
        "name": "tgstat.ru",
        "check_url": f"https://tgstat.ru/en/bot/@{BOT_USERNAME}",
        "keyword": BOT_USERNAME,
        "manual_url": f"https://tgstat.ru/en/bot/@{BOT_USERNAME}",
    },
    {
        "name": "botlist.me",
        "check_url": f"https://botlist.me/bots/{BOT_USERNAME}",
        "keyword": BOT_USERNAME,
        "manual_url": f"https://botlist.me/bots/{BOT_USERNAME}",
    },
    {
        "name": "telegramchannels.me",
        "check_url": f"https://telegramchannels.me/bots/{BOT_USERNAME}",
        "keyword": BOT_USERNAME,
        "manual_url": f"https://telegramchannels.me/bots/{BOT_USERNAME}",
    },
    {
        "name": "tlgrm.ru",
        "check_url": f"https://tlgrm.ru/bots/{BOT_USERNAME}",
        "keyword": BOT_USERNAME,
        "manual_url": f"https://tlgrm.ru/bots/{BOT_USERNAME}",
    },
    {
        "name": "tlgrm.eu",
        "check_url": f"https://tlgrm.eu/bots/{BOT_USERNAME}",
        "keyword": BOT_USERNAME,
        "manual_url": f"https://tlgrm.eu/bots/{BOT_USERNAME}",
    },
    {
        "name": "storebot (Telegram)",
        "check_url": f"https://t.me/{BOT_USERNAME}",
        "keyword": "topbestworkerbot",
        "manual_url": f"https://t.me/{BOT_USERNAME}",
    },
    {
        "name": "bots.business",
        "check_url": f"https://bots.business/bots/{BOT_USERNAME}",
        "keyword": BOT_USERNAME,
        "manual_url": f"https://bots.business/bots/{BOT_USERNAME}",
    },
    {
        "name": "telegrambots.me",
        "check_url": f"https://telegrambots.me/bots/{BOT_USERNAME}",
        "keyword": BOT_USERNAME,
        "manual_url": f"https://telegrambots.me/bots/{BOT_USERNAME}",
    },
    {
        "name": "producthunt.com",
        "check_url": f"https://www.producthunt.com/search?q={BOT_USERNAME}",
        "keyword": "topbestworker",
        "manual_url": "https://www.producthunt.com/",
    },
    {
        "name": "alternativeto.net",
        "check_url": f"https://alternativeto.net/software/{BOT_USERNAME}/",
        "keyword": BOT_USERNAME,
        "manual_url": "https://alternativeto.net/",
    },
]

ARTICLES = [
    {"name": "vc.ru",            "key": "vc.ru"},
    {"name": "habr.com",         "key": "habr.com"},
    {"name": "dtf.ru",           "key": "dtf.ru"},
    {"name": "Reddit /r/TelegramBots", "key": "reddit_telegrambots"},
    {"name": "Reddit /r/resumes",      "key": "reddit_resumes"},
    {"name": "dev.to",           "key": "dev.to"},
    {"name": "medium.com",       "key": "medium.com"},
    {"name": "indiehackers.com", "key": "indiehackers.com"},
]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{'='*60}")
    print(f"  Bot Listings Status Report — {TODAY.isoformat()}")
    print(f"  Bot: @{BOT_USERNAME}")
    print(f"{'='*60}\n")

    submission_date = get_submission_date()
    submitted_str   = days_since(submission_date) if submission_date else "not yet submitted"
    articles_data   = load_articles()

    report_lines = [
        f"Bot Listings Status Report",
        f"Generated: {datetime.datetime.now().isoformat()}",
        f"Bot: @{BOT_USERNAME}",
        f"Submission date: {submission_date or 'unknown'} ({submitted_str})",
        "",
        "=" * 60,
        "DIRECTORY LISTINGS",
        "=" * 60,
    ]

    print("DIRECTORY LISTINGS")
    print("-" * 40)

    dir_found   = 0
    dir_pending = 0
    dir_unknown = 0

    for d in DIRECTORIES:
        name   = d["name"]
        url    = d["check_url"]
        kw     = d["keyword"]
        status_code = check_url_status(url)
        found       = status_code == 200 and check_url(url, kw)

        if found:
            status_str = "✅ LISTED"
            dir_found += 1
        elif status_code in (200, 404):
            status_str = f"❌ PENDING (submitted {submitted_str})"
            dir_pending += 1
        else:
            status_str = f"⚠️  UNKNOWN (HTTP {status_code})"
            dir_unknown += 1

        line = f"  {name:<30} {status_str}"
        print(line)
        report_lines.append(line)

    print()
    print("=" * 40)
    print("ARTICLE POSTS")
    print("-" * 40)

    report_lines += [
        "",
        "=" * 60,
        "ARTICLE POSTS",
        "=" * 60,
    ]

    art_posted  = 0
    art_pending = 0

    for art in ARTICLES:
        name  = art["name"]
        key   = art["key"]
        data  = articles_data.get(key, {})
        posted = data.get("posted", False)
        url    = data.get("url", "")
        date   = data.get("date", "")

        if posted:
            status_str = f"✅ POSTED ({date})"
            if url:
                status_str += f" → {url}"
            art_posted += 1
        else:
            status_str = "📝 NOT YET POSTED"
            art_pending += 1

        line = f"  {name:<30} {status_str}"
        print(line)
        report_lines.append(line)

    # Summary
    total_listed = dir_found + art_posted
    summary = [
        "",
        "=" * 60,
        "SUMMARY",
        "=" * 60,
        f"  Directories listed:  {dir_found}/{len(DIRECTORIES)}",
        f"  Directories pending: {dir_pending}",
        f"  Articles posted:     {art_posted}/{len(ARTICLES)}",
        f"  Articles pending:    {art_pending}",
        "",
        f"  Submission date: {submission_date or 'unknown'} ({submitted_str})",
        f"  Bot link: {BOT_LINK}",
        f"  Report saved to: {REPORT_FILE.name}",
    ]

    report_lines += summary
    for line in summary:
        print(line)

    # Save report
    REPORT_FILE.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n  Report saved to: {REPORT_FILE}")

    # Telegram notification
    tg_lines = [
        f"<b>📊 Listings Status Report</b>",
        f"<code>{TODAY.isoformat()}</code>",
        f"",
        f"📁 Directories: {dir_found}/{len(DIRECTORIES)} listed",
        f"⏳ Pending: {dir_pending} directories",
        f"",
        f"📝 Articles: {art_posted}/{len(ARTICLES)} posted",
        f"⏳ Pending: {art_pending} articles",
        f"",
        f"📅 Submitted: {submitted_str}",
        f"🔗 Bot: @{BOT_USERNAME}",
    ]
    tg_text = "\n".join(tg_lines)
    sent = tg_send(ADMIN_CHAT_ID, tg_text)
    print(f"\n  Telegram notification: {'✅ sent' if sent else '❌ failed'}")

    # Hint: how to mark articles as posted
    print("\n" + "=" * 60)
    print("TIP: To mark an article as posted, edit seo/posted_articles.json:")
    print('  "vc.ru": {"posted": true, "url": "https://vc.ru/...", "date": "2024-01-15"}')
    print("=" * 60)


if __name__ == "__main__":
    main()
