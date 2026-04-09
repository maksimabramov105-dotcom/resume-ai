#!/usr/bin/env python3
"""
submit_directories.py — AutoApply/ResumeAI directory submission
For each directory: try automated GET check, attempt POST if simple form found,
generate manual submission template saved to seo/manual_submissions/
"""
import requests
import os
import json
import time
from datetime import datetime
from pathlib import Path

BOT_CONFIG = {
    "username": "topbestworkerbot",
    "name_ru": "РезюмеАИ — AI Карьерный Консультант",
    "name_en": "ResumeAI — AI Career Consultant",
    "tagline_ru": "Авторассылка резюме + AI резюме за 30 сек. hh.ru + LinkedIn + Indeed",
    "tagline_en": "Auto-apply to 500 jobs/day + AI resume in 30 sec. hh.ru + LinkedIn + Indeed",
    "desc_ru": (
        "Два продукта в одном: РезюмеАИ создаёт уникальное резюме под каждую вакансию "
        "за 30 секунд. АвтоОтклик автоматически рассылает заявки на hh.ru, SuperJob, "
        "LinkedIn, Indeed пока вы спите. Бесплатный тариф: 3 заявки/день."
    ),
    "desc_en": (
        "Two products in one: ResumeAI creates unique tailored resumes in 30 seconds. "
        "AutoApply sends applications to hh.ru, SuperJob, LinkedIn, Indeed automatically. "
        "Free plan: 3 applications/day."
    ),
    "bot_link": "https://t.me/topbestworkerbot",
    "web_link": "https://resumeai.bot",
    "app_link": "https://resumeai.bot/app",
    "category": "Career / Productivity / AI",
    "tags": [
        "resume", "AI", "career", "jobs", "CV", "interview",
        "autoapply", "hh.ru", "job search", "telegram bot",
    ],
}

DIRECTORIES = [
    {
        "name": "Telegram Store",
        "url": "https://t.me/storebot?start=topbestworkerbot",
        "submit_url": None,
        "method": "manual",
        "notes": "Open in Telegram and submit via @storebot",
    },
    {
        "name": "Telegram Bots (tlgrm.ru)",
        "url": "https://tlgrm.ru/bots",
        "submit_url": "https://tlgrm.ru/bots/add",
        "method": "post",
        "notes": "Form submission with bot username and description",
    },
    {
        "name": "Tgstat.ru",
        "url": "https://tgstat.ru",
        "submit_url": "https://tgstat.ru/bot/add",
        "method": "manual",
        "notes": "Register account first, then add bot via dashboard",
    },
    {
        "name": "Combot.org",
        "url": "https://combot.org",
        "submit_url": "https://combot.org/telegram/bot/topbestworkerbot",
        "method": "auto",
        "notes": "Auto-indexed when bot has activity",
    },
    {
        "name": "Telegram Catalog (tgcat.ru)",
        "url": "https://tgcat.ru",
        "submit_url": "https://tgcat.ru/add",
        "method": "post",
        "notes": "Submit bot link and description",
    },
    {
        "name": "Tchannels.ru",
        "url": "https://tchannels.ru",
        "submit_url": "https://tchannels.ru/bots/add",
        "method": "manual",
        "notes": "Free listing, requires account registration",
    },
    {
        "name": "Telega.in",
        "url": "https://telega.in",
        "submit_url": "https://telega.in/catalog/add",
        "method": "post",
        "notes": "Catalog for Telegram bots and channels",
    },
    {
        "name": "BotList (botlist.me)",
        "url": "https://www.botlist.me",
        "submit_url": "https://www.botlist.me/bots/new",
        "method": "manual",
        "notes": "Register and submit, has upvote system",
    },
    {
        "name": "Telegram Bots Hub",
        "url": "https://telegrambotslist.com",
        "submit_url": "https://telegrambotslist.com/submit",
        "method": "post",
        "notes": "English-language directory",
    },
    {
        "name": "Product Hunt",
        "url": "https://www.producthunt.com",
        "submit_url": "https://www.producthunt.com/posts/new",
        "method": "manual",
        "notes": "High-value launch — prepare screenshots and tagline",
    },
    {
        "name": "There's An AI For That",
        "url": "https://theresanaiforthat.com",
        "submit_url": "https://theresanaiforthat.com/submit/",
        "method": "post",
        "notes": "AI tool directory — good for international SEO",
    },
    {
        "name": "Futurepedia",
        "url": "https://www.futurepedia.io",
        "submit_url": "https://www.futurepedia.io/submit-tool",
        "method": "post",
        "notes": "Large AI tools directory",
    },
    {
        "name": "AI Tools Directory (aitoolsdirectory.com)",
        "url": "https://aitoolsdirectory.com",
        "submit_url": "https://aitoolsdirectory.com/submit",
        "method": "post",
        "notes": "Free submission",
    },
    {
        "name": "GetApp",
        "url": "https://www.getapp.com",
        "submit_url": "https://www.getapp.com/for-vendors/",
        "method": "manual",
        "notes": "Business software directory — good for B2B exposure",
    },
    {
        "name": "AlternativeTo",
        "url": "https://alternativeto.net",
        "submit_url": "https://alternativeto.net/software/resumeai-bot/add/",
        "method": "manual",
        "notes": "Add as alternative to resume builders and job search tools",
    },
    {
        "name": "G2.com",
        "url": "https://www.g2.com",
        "submit_url": "https://sell.g2.com/list-your-product",
        "method": "manual",
        "notes": "Major B2B review platform — high domain authority",
    },
]

OUTPUT_DIR = Path(__file__).parent / "manual_submissions"
OUTPUT_DIR.mkdir(exist_ok=True)


def _check_url_accessible(url: str, timeout: int = 8) -> tuple[bool, int]:
    """Try a GET request. Returns (accessible, status_code)."""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; ResumeAI-Bot-Submitter/1.0; "
                "+https://resumeai.bot)"
            )
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return True, resp.status_code
    except requests.exceptions.SSLError:
        return False, -1
    except requests.exceptions.ConnectionError:
        return False, 0
    except requests.exceptions.Timeout:
        return False, -2
    except Exception:
        return False, -3


def _try_automated_submit(directory: dict) -> tuple[bool, str]:
    """
    Attempt a simple automated POST if the directory supports it.
    Returns (success, message).
    """
    submit_url = directory.get("submit_url")
    if not submit_url or directory.get("method") != "post":
        return False, "manual submission required"

    try:
        payload = {
            "url": BOT_CONFIG["bot_link"],
            "name": BOT_CONFIG["name_en"],
            "description": BOT_CONFIG["desc_en"],
            "category": BOT_CONFIG["category"],
            "tags": ", ".join(BOT_CONFIG["tags"][:5]),
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; ResumeAI-Bot-Submitter/1.0; "
                "+https://resumeai.bot)"
            ),
            "Content-Type": "application/x-www-form-urlencoded",
        }
        resp = requests.post(
            submit_url, data=payload, headers=headers, timeout=10, allow_redirects=True
        )
        if resp.status_code in (200, 201, 302):
            return True, f"POST returned HTTP {resp.status_code}"
        return False, f"POST returned HTTP {resp.status_code}"
    except Exception as e:
        return False, f"POST failed: {e}"


def _generate_template(directory: dict) -> str:
    """Generate a full pre-filled submission template string."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    name = directory["name"]
    url = directory["url"]
    submit_url = directory.get("submit_url", "see notes")
    notes = directory.get("notes", "")
    tags_str = ", ".join(BOT_CONFIG["tags"])

    return f"""
{'=' * 55}
SUBMISSION: {name}
URL: {url}
SUBMIT AT: {submit_url}
DATE: {ts}
{'=' * 55}

--- ENGLISH ---

BOT USERNAME:  @{BOT_CONFIG["username"]}
BOT LINK:      {BOT_CONFIG["bot_link"]}
WEBSITE:       {BOT_CONFIG["web_link"]}

NAME:          {BOT_CONFIG["name_en"]}
TAGLINE:       {BOT_CONFIG["tagline_en"]}

SHORT DESC (160 chars):
AI Telegram bot: tailored resume in 30 sec + auto-apply to 500 jobs/day on hh.ru, LinkedIn, Indeed. Free plan: 3 apps/day.

FULL DESCRIPTION:
{BOT_CONFIG["desc_en"]}

CATEGORY:      {BOT_CONFIG["category"]}
TAGS:          {tags_str}

--- RUSSIAN ---

ИМЯ:          {BOT_CONFIG["name_ru"]}
СЛОГАН:       {BOT_CONFIG["tagline_ru"]}

КРАТКОЕ ОПИСАНИЕ (160 символов):
AI Telegram бот: резюме под вакансию за 30 сек + авторассылка на 500 вакансий/день. hh.ru, SuperJob, LinkedIn. Бесплатно: 3 заявки.

ПОЛНОЕ ОПИСАНИЕ:
{BOT_CONFIG["desc_ru"]}

--- NOTES ---
{notes}

{'=' * 55}
""".strip()


def main():
    print("\n" + "=" * 55)
    print("  DIRECTORY SUBMISSION TOOL — ResumeAI Bot")
    print("=" * 55)
    print(f"  Bot: @{BOT_CONFIG['username']}")
    print(f"  Total directories: {len(DIRECTORIES)}")
    print("=" * 55 + "\n")

    automated_success = 0
    manual_needed = 0
    results = []

    for i, directory in enumerate(DIRECTORIES, 1):
        name = directory["name"]
        url = directory["url"]
        print(f"[{i:02d}/{len(DIRECTORIES)}] {name}")
        print(f"       URL: {url}")

        # Step 1: Check if accessible
        accessible, status = _check_url_accessible(url)
        if accessible:
            print(f"       Accessible: YES (HTTP {status})")
        else:
            print(f"       Accessible: NO (code={status})")

        # Step 2: Try automated submission
        auto_ok = False
        if accessible and directory.get("method") == "post":
            auto_ok, msg = _try_automated_submit(directory)
            if auto_ok:
                print(f"       Auto-submit: SUCCESS — {msg}")
                automated_success += 1
            else:
                print(f"       Auto-submit: FAILED — {msg}")

        if not auto_ok:
            manual_needed += 1

        # Step 3: Always generate a template
        template = _generate_template(directory)
        safe_name = name.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(".", "")
        out_file = OUTPUT_DIR / f"{i:02d}_{safe_name}.txt"
        out_file.write_text(template, encoding="utf-8")
        print(f"       Template:    {out_file}")

        results.append({
            "directory": name,
            "accessible": accessible,
            "auto_submitted": auto_ok,
            "template": str(out_file),
        })

        print()
        time.sleep(0.5)  # Be polite to servers

    # Save JSON summary
    summary_file = OUTPUT_DIR / "_summary.json"
    summary_file.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Print summary table
    print("\n" + "=" * 55)
    print("  SUBMISSION SUMMARY")
    print("=" * 55)
    print(f"  Automated success:  {automated_success}/{len(DIRECTORIES)}")
    print(f"  Manual needed:      {manual_needed}/{len(DIRECTORIES)}")
    print(f"  Templates saved to: {OUTPUT_DIR}/")
    print(f"  JSON summary:       {summary_file}")
    print("=" * 55)
    print("\nNext steps:")
    print("  1. Open each .txt file in seo/manual_submissions/")
    print("  2. Copy-paste the pre-filled content into each directory's form")
    print("  3. Mark completed in _summary.json")
    print()


if __name__ == "__main__":
    main()
