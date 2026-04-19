#!/usr/bin/env python3
"""
auto_blogger.py — Runs daily at 06:30 UTC.
Generates SEO blog posts via GPT-4o-mini and saves them for the Next.js site.
"""
import hashlib
import json
import os
import random
from datetime import datetime
from pathlib import Path

from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY", "")
OPENAI_BASE    = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else None
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")

BLOG_DIR = Path(os.getenv("BLOG_DIR", Path(__file__).parent.parent / "landing" / "blog"))
KEYWORDS_FILE = Path(__file__).parent.parent / "data" / "seo_keywords.json"
USED_FILE = BLOG_DIR / "_used_keywords.json"

BLOG_DIR.mkdir(parents=True, exist_ok=True)


def _get_client() -> OpenAI:
    kwargs = {"api_key": OPENAI_API_KEY}
    if OPENAI_BASE:
        kwargs["base_url"] = OPENAI_BASE
    return OpenAI(**kwargs)


def _get_next_keyword() -> str:
    keywords = json.loads(KEYWORDS_FILE.read_text()) if KEYWORDS_FILE.exists() else []
    used: list = json.loads(USED_FILE.read_text()) if USED_FILE.exists() else []
    available = [k for k in keywords if k not in used]
    if not available:
        used = []
        available = keywords[:]
    keyword = random.choice(available) if available else "AI job search automation"
    used.append(keyword)
    USED_FILE.write_text(json.dumps(used))
    return keyword


def _generate_post(client: OpenAI, keyword: str) -> dict:
    prompt = f"""Write a helpful, practical blog post targeting this SEO keyword: "{keyword}"

Requirements:
- 800-1000 words
- Title: H1 that naturally includes the keyword
- 4-5 H2 subheadings
- Conversational but authoritative tone
- Include 1-2 mentions of "ResumeAI Bot" as a tool that helps with this (natural, not spammy)
- End with a CTA: "Try ResumeAI Bot free at t.me/topbestworkerbot"
- Return valid JSON with these exact keys:
  title, slug (lowercase hyphens 4-6 words), meta_description (max 155 chars), content_html (full HTML)
"""
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    return json.loads(response.choices[0].message.content)


def _save_post(post: dict, keyword: str) -> None:
    slug = post.get("slug") or hashlib.md5(keyword.encode()).hexdigest()[:8]
    today = datetime.utcnow()
    post.update({
        "keyword": keyword,
        "published_at": today.isoformat(),
        "author": "ResumeAI Team",
    })
    filename = f"{today.strftime('%Y-%m-%d')}-{slug}.json"
    (BLOG_DIR / filename).write_text(json.dumps(post, ensure_ascii=False, indent=2))
    print(f"[auto_blogger] Saved: {filename}")

    # Update index
    index_path = BLOG_DIR / "index.json"
    index: list = json.loads(index_path.read_text()) if index_path.exists() else []
    index.insert(0, {
        "slug": slug,
        "title": post.get("title", ""),
        "meta_description": post.get("meta_description", ""),
        "published_at": post["published_at"],
        "filename": filename,
    })
    index_path.write_text(json.dumps(index[:50], ensure_ascii=False, indent=2))


def run_auto_blogger() -> None:
    if not OPENAI_API_KEY:
        print("[auto_blogger] No API key — skipping")
        return
    try:
        client = _get_client()
        keyword = _get_next_keyword()
        print(f"[auto_blogger] Generating post for: {keyword}")
        post = _generate_post(client, keyword)
        _save_post(post, keyword)
        print("[auto_blogger] Done.")
    except Exception as e:
        print(f"[auto_blogger] Error: {e}")


if __name__ == "__main__":
    run_auto_blogger()
