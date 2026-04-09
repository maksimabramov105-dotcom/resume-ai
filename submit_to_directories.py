#!/usr/bin/env python3
"""
submit_to_directories.py
Automates submission of ResumeAI bot to Telegram bot directories,
product listing sites, and AI tool aggregators.

Usage:
    python submit_to_directories.py

The script opens each submission URL in your default browser so you can
complete the form (most directories require a human check / CAPTCHA).
It also prints a pre-filled text block you can paste into each form.
"""

import webbrowser
import time
import textwrap

# ── Bot info ────────────────────────────────────────────────────────────
BOT = {
    "name":        "ResumeAI / РезюмеАИ",
    "username":    "@topbestworkerbot",
    "url":         "https://t.me/topbestworkerbot",
    "website":     "https://resumeai.bot",
    "tagline_en":  "AI-powered resume, cover letter & interview prep in Telegram — in 30 seconds",
    "tagline_ru":  "AI-карьерный консультант в Telegram: резюме под вакансию за 30 секунд",
    "description_en": (
        "ResumeAI is an AI career consultant inside Telegram. "
        "It creates ATS-optimised resumes tailored to any job posting in ~30 seconds, "
        "writes personalised cover letters, simulates interviews using the STAR method, "
        "analyses job postings for red flags and hidden requirements, and sends weekly "
        "career digests. Free plan available. Works in Russian and English."
    ),
    "description_ru": (
        "РезюмеАИ — AI-карьерный консультант в Telegram. "
        "Создаёт ATS-оптимизированные резюме под конкретную вакансию за ~30 секунд, "
        "пишет сопроводительные письма, симулирует собеседования по методу STAR, "
        "анализирует вакансии на красные флаги и скрытые требования, "
        "рассылает еженедельный карьерный дайджест. Есть бесплатный тариф."
    ),
    "category":    "Career / Productivity / AI Tools",
    "tags":        "resume, cover letter, interview prep, AI, career, job search, ATS, telegram bot",
    "language":    "Russian, English",
    "price":       "Freemium (free plan + Pro $9/mo + Premium $19/mo)",
    "contact":     "https://t.me/topbestworkerbot",
}

# ── Directories ─────────────────────────────────────────────────────────
DIRECTORIES = [
    # ── Telegram bot directories ──────────────────────────────────────
    {
        "name":   "StoreBot.me",
        "url":    "https://storebot.me/submit",
        "note":   "Largest Telegram bot catalogue. Fill in bot username + description.",
    },
    {
        "name":   "Telegram Bot Store (TelegramBotStore.com)",
        "url":    "https://telegrambotstore.com/add-bot",
        "note":   "Submit @topbestworkerbot, category: Career/Productivity.",
    },
    {
        "name":   "Botlist.co",
        "url":    "https://botlist.co/bots/new",
        "note":   "Popular cross-platform bot directory. Free listing.",
    },
    {
        "name":   "Tgstat.ru (add bot)",
        "url":    "https://tgstat.ru/add",
        "note":   "Russian-language Telegram analytics & catalogue.",
    },
    {
        "name":   "Tlgrm.ru",
        "url":    "https://tlgrm.ru/bots/add",
        "note":   "RU catalogue — paste tagline_ru.",
    },
    # ── AI tool aggregators ───────────────────────────────────────────
    {
        "name":   "There's An AI For That (theresanaiforthat.com)",
        "url":    "https://theresanaiforthat.com/add-tool/",
        "note":   "High-traffic AI tools directory. Very good for SEO backlink.",
    },
    {
        "name":   "FuturePedia",
        "url":    "https://www.futurepedia.io/submit-tool",
        "note":   "Large AI tools directory. Category: Career.",
    },
    {
        "name":   "TopAI.tools",
        "url":    "https://topai.tools/submit",
        "note":   "Curated AI tool listings.",
    },
    {
        "name":   "AI Tool Hunt",
        "url":    "https://www.aitoolhunt.com/submit",
        "note":   "Free submission, quick review.",
    },
    {
        "name":   "Toolify.ai",
        "url":    "https://www.toolify.ai/submit",
        "note":   "High DA site; add in Career / Resume category.",
    },
    {
        "name":   "AITopTools.com",
        "url":    "https://aitoptools.com/submit-tool/",
        "note":   "Straightforward submission form.",
    },
    {
        "name":   "SaaS Hub / Product Hunt",
        "url":    "https://www.producthunt.com/posts/new",
        "note":   "Product Hunt launch — creates buzz and backlinks. Schedule for a Tuesday.",
    },
    # ── Resume / career tool lists ─────────────────────────────────────
    {
        "name":   "Resume Worded Resources",
        "url":    "https://resumeworded.com",
        "note":   "Partner / mention opportunity. Contact via their site.",
    },
    {
        "name":   "Jobscan Blog Tools List",
        "url":    "https://www.jobscan.co/blog/best-resume-tools/",
        "note":   "Reach out to be included in their 'Best AI resume tools' roundup.",
    },
]

# ── Paste block ─────────────────────────────────────────────────────────
PASTE_BLOCK = f"""
╔══════════════════════════════════════════════════════════════╗
  ResumeAI — Quick-paste submission block
╚══════════════════════════════════════════════════════════════╝

Bot username : {BOT['username']}
Bot URL      : {BOT['url']}
Website      : {BOT['website']}
Category     : {BOT['category']}
Tags         : {BOT['tags']}
Language     : {BOT['language']}
Pricing      : {BOT['price']}

── Tagline (EN) ────────────────────────────────────────────────
{BOT['tagline_en']}

── Tagline (RU) ────────────────────────────────────────────────
{BOT['tagline_ru']}

── Description (EN, ~100 words) ────────────────────────────────
{textwrap.fill(BOT['description_en'], 72)}

── Description (RU, ~100 words) ────────────────────────────────
{textwrap.fill(BOT['description_ru'], 72)}

── Contact / Support ───────────────────────────────────────────
{BOT['contact']}
"""

# ── Main ─────────────────────────────────────────────────────────────────
def main():
    print(PASTE_BLOCK)
    print("=" * 66)
    print(f"  Opening {len(DIRECTORIES)} submission pages in your browser...")
    print("  Each page opens with a 2-second gap to avoid rate limits.")
    print("=" * 66)
    print()

    for i, d in enumerate(DIRECTORIES, 1):
        print(f"[{i:02d}/{len(DIRECTORIES)}] {d['name']}")
        print(f"        URL  : {d['url']}")
        print(f"        Note : {d['note']}")
        print()
        try:
            webbrowser.open(d["url"])
        except Exception as e:
            print(f"        ⚠ Could not open browser: {e}")
        time.sleep(2)

    print("=" * 66)
    print("  Done! Complete each form using the paste block above.")
    print("  Tip: bookmark this script — re-run whenever you add features.")
    print("=" * 66)


if __name__ == "__main__":
    main()
