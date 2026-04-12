#!/usr/bin/env python3
"""Weekly blog post generator — run via cron every Monday."""
import httpx, os, sys

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
API_URL = "https://resumeai-bot.ru/api/admin/generate-blog-post"

if __name__ == "__main__":
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    try:
        r = httpx.post(API_URL, json={"topic": topic}, headers={"X-Admin-Secret": ADMIN_SECRET}, timeout=90)
        print(r.status_code, r.text[:500])
    except Exception as e:
        print(f"Error: {e}")
