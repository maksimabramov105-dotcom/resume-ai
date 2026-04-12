"""
marketing_cron.py — Daily marketing automation for resumeai-bot.ru
Runs at 06:00 UTC (09:00 Moscow) every day.

Jobs:
1. Post daily tip to Telegram channel @resumeai_channel
2. Post daily tip to VK community club237549969
3. Send digest email to opted-in users (drip step advancement)
4. Log summary stats

Scheduling:
  systemd timer OR APScheduler (started from autoapply_main.py on startup)
  Standalone: python3 marketing_cron.py  (runs once immediately)
"""

import asyncio
import logging
import os
import random
import sys
from datetime import datetime, timezone

import httpx

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [marketing_cron] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
TG_CHANNEL       = os.getenv("TG_CHANNEL", "@resumeai_channel")
VK_TOKEN         = os.getenv("VK_API_TOKEN", "")
VK_GROUP_ID      = os.getenv("VK_GROUP_ID", "237549969")
WEBAPP_URL        = os.getenv("WEBAPP_BASE_URL", "https://resumeai-bot.ru")
AUTOAPPLY_API    = os.getenv("AUTOAPPLY_API", "http://127.0.0.1:8080")
ADMIN_SECRET     = os.getenv("ADMIN_SECRET", "")

# ── Daily tips pool ───────────────────────────────────────────────────────────
DAILY_TIPS = [
    ("📄 Совет дня: Резюме без ATS-ключевых слов", (
        "Большинство резюме отсеиваются до того, как их увидит рекрутер. "
        "Проверьте ATS-скор своего резюме бесплатно и узнайте, какие слова добавить."
    )),
    ("🎯 Совет дня: Сопроводительное письмо", (
        "Кандидаты с персональным сопроводительным письмом получают ответ в 2.5× чаще. "
        "AI напишет его под вашу вакансию за 15 секунд."
    )),
    ("🤖 Совет дня: Авто-отклики на hh.ru", (
        "Пока конкуренты откликаются вручную, ваш бот уже отправил 50 заявок. "
        "Попробуйте АвтоОтклик — первые 3 отклика бесплатно."
    )),
    ("📊 Совет дня: Статистика поиска работы", (
        "Средний кандидат тратит 3 часа в день на ручные отклики. "
        "С AI это занимает 5 минут. Освободите время для подготовки к собеседованиям."
    )),
    ("💼 Совет дня: Профиль на hh.ru", (
        "Резюме с фото получают на 40% больше просмотров. "
        "Но важнее — правильный заголовок. Что вы пишете в первой строке?"
    )),
    ("🎤 Совет дня: Подготовка к собеседованию", (
        "«Расскажите о себе» — 90% кандидатов отвечают неправильно. "
        "Потренируйтесь с AI-симулятором собеседования — задаёт реальные вопросы."
    )),
    ("🔥 Совет дня: Горячие вакансии недели", (
        "IT, финансы, маркетинг — рынок активен. "
        "Поставьте авто-мониторинг вакансий и получайте лучшие первым."
    )),
]


async def post_to_telegram(text: str) -> bool:
    """Post message to Telegram channel."""
    if not BOT_TOKEN:
        logger.warning("[tg] BOT_TOKEN not set — skipping Telegram post")
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": TG_CHANNEL,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False,
                },
            )
        data = resp.json()
        if data.get("ok"):
            logger.info("[tg] posted to %s ok", TG_CHANNEL)
            return True
        logger.error("[tg] error: %s", data)
        return False
    except Exception as exc:
        logger.error("[tg] exception: %s", exc)
        return False


async def post_to_vk(text: str) -> bool:
    """Post message to VK community."""
    if not VK_TOKEN:
        logger.warning("[vk] VK_API_TOKEN not set — skipping VK post")
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.vk.com/method/wall.post",
                data={
                    "owner_id": f"-{VK_GROUP_ID}",
                    "message": text,
                    "from_group": 1,
                    "access_token": VK_TOKEN,
                    "v": "5.131",
                },
            )
        data = resp.json()
        if "response" in data:
            post_id = data["response"].get("post_id")
            logger.info("[vk] posted to club%s, post_id=%s", VK_GROUP_ID, post_id)
            return True
        logger.error("[vk] error: %s", data.get("error"))
        return False
    except Exception as exc:
        logger.error("[vk] exception: %s", exc)
        return False


def _pick_tip() -> tuple[str, str]:
    """Pick today's tip based on day-of-year for consistent daily rotation."""
    day = datetime.now(timezone.utc).timetuple().tm_yday
    return DAILY_TIPS[day % len(DAILY_TIPS)]


async def run_daily_marketing() -> None:
    """Main daily job — called by cron/scheduler."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    logger.info("=== daily marketing run at %s ===", now)

    title, body = _pick_tip()
    cta_url = f"{WEBAPP_URL}?utm_source=daily_tip&utm_medium=social&utm_campaign=tips"

    # Telegram message
    tg_text = (
        f"<b>{title}</b>\n\n"
        f"{body}\n\n"
        f'<a href="{cta_url}">Попробовать бесплатно →</a>'
    )
    tg_ok = await post_to_telegram(tg_text)

    # VK message (no HTML)
    vk_text = f"{title}\n\n{body}\n\n{cta_url}"
    vk_ok = await post_to_vk(vk_text)

    logger.info("daily marketing done — tg=%s vk=%s", tg_ok, vk_ok)


# ── APScheduler integration ───────────────────────────────────────────────────
def setup_marketing_scheduler(scheduler) -> None:
    """Add daily 9 AM Moscow (6 AM UTC) job to an existing APScheduler instance."""
    scheduler.add_job(
        lambda: asyncio.create_task(run_daily_marketing()),
        trigger="cron",
        hour=6,
        minute=0,
        id="daily_marketing",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("[marketing_cron] daily job scheduled at 06:00 UTC (09:00 Moscow)")


# ── Standalone run ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(run_daily_marketing())
