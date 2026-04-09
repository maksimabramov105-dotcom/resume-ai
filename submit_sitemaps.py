#!/usr/bin/env python3
"""
submit_sitemaps.py — Submit sitemap to Google, Yandex, and Bing
No API auth required for basic ping submission.

Usage: python3 submit_sitemaps.py
Or with custom URL: python3 submit_sitemaps.py https://resumeai.bot/sitemap.xml
"""
import sys, requests, datetime

SITEMAP_URL = sys.argv[1] if len(sys.argv) > 1 else "https://resumeai.bot/sitemap.xml"
SITE_URL    = "https://resumeai.bot"
WEBMASTER_FILE = "webmaster_setup.txt"

ENGINES = [
    ("Google", f"https://www.google.com/ping?sitemap={SITEMAP_URL}"),
    ("Yandex", f"https://webmaster.yandex.com/ping?sitemap={SITEMAP_URL}"),
    ("Bing",   f"https://www.bing.com/ping?sitemap={SITEMAP_URL}"),
]

results = {}
for name, url in ENGINES:
    try:
        r = requests.get(url, timeout=10)
        results[name] = f"✅ {r.status_code}"
    except Exception as e:
        results[name] = f"❌ {e}"

print(f"""✅ Sitemap submitted to:
 - Google: {results['Google']}
 - Yandex: {results['Yandex']}
 - Bing:   {results['Bing']}

Next step: verify ownership in each webmaster tool.
Instructions saved to: {WEBMASTER_FILE}""")

# Write webmaster_setup.txt
INSTRUCTIONS = """
WEBMASTER TOOLS SETUP — ResumeAI (resumeai.bot)
Generated: {date}
Sitemap: {sitemap}
================================================

1. GOOGLE SEARCH CONSOLE
========================
URL: https://search.google.com/search-console
Steps:
  1. Click "Add property" → choose "URL prefix" → enter: https://resumeai.bot
  2. Choose verification method: "HTML tag"
  3. Copy the meta tag: <meta name="google-site-verification" content="XXXXX" />
  4. Open landing/index.html, find: GOOGLE_VERIFICATION_TOKEN_HERE
  5. Replace with your actual token from Google
  6. Deploy updated index.html (push to GitHub Pages)
  7. Back in Search Console → click "Verify"
  8. Go to Sitemaps → enter: sitemap.xml → Submit

2. YANDEX WEBMASTER
===================
URL: https://webmaster.yandex.ru
Steps:
  1. Click "+ Добавить сайт" → enter: https://resumeai.bot
  2. Choose "HTML-метатег" verification
  3. Copy the content value from the meta tag shown
  4. Open landing/index.html, find: YANDEX_VERIFICATION_TOKEN_HERE
  5. Replace with your actual Yandex token
  6. Deploy updated index.html
  7. Click "Проверить"
  8. Go to Индексирование → Файл Sitemap → add: sitemap.xml

3. BING WEBMASTER TOOLS
========================
URL: https://www.bing.com/webmasters
Steps:
  1. Sign in with Microsoft account
  2. Add your site: https://resumeai.bot
  3. Choose "XML file" or "Meta tag" verification
  4. For meta tag: copy content value
  5. Open landing/index.html, find: BING_VERIFICATION_TOKEN_HERE
  6. Replace with your Bing token
  7. Deploy and verify
  8. Go to Sitemaps → Submit sitemap → enter: {sitemap}

IMPORTANT: After verifying, it takes 3-7 days for Google/Bing to
index your pages. Yandex may take up to 2 weeks for new sites.
""".format(date=datetime.datetime.now().strftime("%Y-%m-%d"), sitemap=SITEMAP_URL)

with open(WEBMASTER_FILE, "w", encoding="utf-8") as f:
    f.write(INSTRUCTIONS)
