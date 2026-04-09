#!/usr/bin/env python3
"""
telegraph_publisher.py — Publishes articles to Telegra.ph.

Telegra.ph is free, no account required — just a token stored locally.
Creates a token on first run, saves to logs/telegraph_token.txt.
Publishes max 2 articles per week.

Usage:
    python3 telegraph_publisher.py           # publish next unpublished article
    python3 telegraph_publisher.py --dry-run # preview without publishing
"""

import json
import logging
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import urllib.request
import urllib.parse

sys.path.insert(0, str(Path(__file__).parent.parent))

from content_marketing.config import (
    BOT_LINK,
    BOT_NAME,
    CONTENT_DIR,
    LOGS_DIR,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "telegraph_log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

TOKEN_FILE     = LOGS_DIR / "telegraph_token.txt"
PUBLISHED_LOG  = LOGS_DIR / "telegraph_published.json"
TELEGRAPH_API  = "https://api.telegra.ph"

AUTHOR_NAME = "РезюмеАИ Команда"
AUTHOR_URL  = BOT_LINK

MAX_PER_WEEK = 2


# ── Telegraph API calls ───────────────────────────────────────────────────────

def _api_call(method: str, params: dict) -> dict:
    """Make a POST request to the Telegraph API. Returns the response dict."""
    url = f"{TELEGRAPH_API}/{method}"
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_or_create_token() -> str:
    """
    Load existing Telegraph token or create a new account.
    Token is saved to logs/telegraph_token.txt.
    """
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if token:
            log.info("Using existing Telegraph token: %s…", token[:10])
            return token

    log.info("Creating new Telegraph account…")
    result = _api_call("createAccount", {
        "short_name": "ResumeAI",
        "author_name": AUTHOR_NAME,
        "author_url":  AUTHOR_URL,
    })

    if not result.get("ok"):
        raise RuntimeError(f"Failed to create Telegraph account: {result}")

    token = result["result"]["access_token"]
    TOKEN_FILE.write_text(token, encoding="utf-8")
    log.info("✅ Telegraph token created and saved.")
    return token


def markdown_to_nodes(text: str) -> list:
    """
    Convert simple markdown text to Telegraph content nodes.
    Supports: ## headings, **bold**, plain paragraphs.
    Telegraph uses a JSON node format for rich content.
    """
    nodes = []
    paragraphs = text.split("\n\n")

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # ## Heading → h3 node
        if para.startswith("## "):
            heading_text = para[3:].strip()
            nodes.append({"tag": "h3", "children": [heading_text]})
            continue

        # # Heading → h4 node
        if para.startswith("# "):
            heading_text = para[2:].strip()
            nodes.append({"tag": "h4", "children": [heading_text]})
            continue

        # Handle inline bold (**text**) within paragraph
        children = []
        remaining = para
        bold_pattern = re.compile(r"\*\*(.+?)\*\*")

        while remaining:
            match = bold_pattern.search(remaining)
            if not match:
                if remaining:
                    children.append(remaining)
                break
            # Text before bold
            before = remaining[:match.start()]
            if before:
                children.append(before)
            # Bold node
            children.append({"tag": "b", "children": [match.group(1)]})
            remaining = remaining[match.end():]

        if not children:
            children = [para]

        # Wrap links to Telegram in <a> tags
        final_children = []
        for child in children:
            if isinstance(child, str) and "t.me/" in child:
                # Linkify t.me/... URLs
                parts = re.split(r"(https?://t\.me/\S+|t\.me/\S+)", child)
                for part in parts:
                    if part.startswith("http") and "t.me/" in part:
                        final_children.append({"tag": "a", "attrs": {"href": part}, "children": [part]})
                    elif "t.me/" in part and not part.startswith("http"):
                        href = "https://" + part
                        final_children.append({"tag": "a", "attrs": {"href": href}, "children": [part]})
                    elif part:
                        final_children.append(part)
            else:
                final_children.append(child)

        nodes.append({"tag": "p", "children": final_children if final_children else children})

    return nodes


def load_published_log() -> dict:
    if PUBLISHED_LOG.exists():
        return json.loads(PUBLISHED_LOG.read_text(encoding="utf-8"))
    return {}


def save_published_log(data: dict) -> None:
    PUBLISHED_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def posts_this_week(published: dict) -> int:
    """Count how many articles were published this ISO week."""
    current_week = date.today().isocalendar()[:2]  # (year, week)
    count = 0
    for entry in published.values():
        pub_date = entry.get("published_at", "")[:10]
        try:
            w = date.fromisoformat(pub_date).isocalendar()[:2]
            if w == current_week:
                count += 1
        except (ValueError, AttributeError):
            pass
    return count


def get_next_article() -> tuple[str, str, str] | None:
    """
    Find the oldest unpublished telegraph_article.txt.
    Returns (folder_name, title, body) or None.
    """
    published = load_published_log()
    already_done = set(published.keys())

    folders = sorted(
        [d for d in CONTENT_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name
    )

    for folder in folders:
        art_file = folder / "telegraph_article.txt"
        if not art_file.exists():
            continue
        if folder.name in already_done:
            continue

        content = art_file.read_text(encoding="utf-8")

        # Parse TITLE: line
        title = ""
        body_lines = []
        for line in content.splitlines():
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            else:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        if not title:
            # Fallback: use first line as title
            title = body_lines[0].strip() if body_lines else "Статья о карьере"
            body = "\n".join(body_lines[1:]).strip()

        return folder.name, title, body

    return None


def publish_article(title: str, body: str, dry_run: bool = False) -> str | None:
    """
    Publish article to Telegra.ph. Returns published URL or None.
    """
    if dry_run:
        log.info("[DRY RUN] Would publish:\nTITLE: %s\nBODY: %s…", title, body[:200])
        return "https://telegra.ph/dry-run-article"

    token = get_or_create_token()
    nodes = markdown_to_nodes(body)
    content_json = json.dumps(nodes, ensure_ascii=False)

    result = _api_call("createPage", {
        "access_token": token,
        "title":        title,
        "author_name":  AUTHOR_NAME,
        "author_url":   AUTHOR_URL,
        "content":      content_json,
        "return_content": "false",
    })

    if not result.get("ok"):
        raise RuntimeError(f"Telegraph createPage failed: {result}")

    url = result["result"]["url"]
    log.info("✅ Published: %s", url)
    return url


def main(dry_run: bool = False):
    published = load_published_log()

    # Check weekly limit
    week_count = posts_this_week(published)
    if week_count >= MAX_PER_WEEK:
        log.info("Already published %d/%d articles this week — skipping.", week_count, MAX_PER_WEEK)
        return

    result = get_next_article()
    if not result:
        log.info("No unpublished articles found. Run content_generator.py first.")
        return

    folder_name, title, body = result
    log.info("Publishing: '%s'", title[:80])

    url = publish_article(title, body, dry_run=dry_run)
    if url:
        published[folder_name] = {
            "title": title[:100],
            "url": url,
            "published_at": datetime.now(timezone.utc).isoformat(),
        }
        save_published_log(published)
        log.info("Saved to published log.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
