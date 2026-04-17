#!/usr/bin/env python3
"""Health monitor — run every 30 minutes via cron."""
import httpx, asyncio, os
from datetime import datetime

ENDPOINTS = [
    "https://resumeai-bot.ru/",
    "https://resumeai-bot.ru/app",
    "https://resumeai-bot.ru/api/health",
    "https://resumeai-bot.ru/sitemap.xml",
    "https://resumeai-bot.ru/blog/",
    "https://resumeai-bot.ru/robots.txt",
]

async def check_health():
    issues = []
    async with httpx.AsyncClient(timeout=10) as client:
        for url in ENDPOINTS:
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    issues.append(f"❌ {url} → {r.status_code}")
            except Exception as e:
                issues.append(f"💀 {url} → {str(e)}")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    if issues:
        bot_token = os.getenv("BOT_TOKEN", "")
        admin_id = os.getenv("ADMIN_TELEGRAM_ID", os.getenv("ADMIN_ID", "0"))
        msg = f"🚨 [{ts}] HEALTH CHECK FAILED:\n" + "\n".join(issues)
        print(msg)
        if bot_token and admin_id:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": admin_id, "text": msg}
                    )
            except Exception as e:
                print(f"Telegram alert failed: {e}")
    else:
        print(f"✅ [{ts}] All {len(ENDPOINTS)} endpoints healthy")

if __name__ == "__main__":
    asyncio.run(check_health())
