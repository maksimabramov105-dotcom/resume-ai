"""
run.py — запускает бота и FastAPI сервер параллельно.
Использование: python run.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# Make both bot/ and repo root importable
ROOT = os.path.dirname(os.path.abspath(__file__))
BOT_DIR = os.path.join(ROOT, "bot")
if BOT_DIR not in sys.path:
    sys.path.insert(0, BOT_DIR)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BOT_TOKEN  # flat import (bot/ is in sys.path)
from database.db import init_db
from handlers import start, resume, cover_letter, interview, vacancy_analysis, ai_assistant, payment, profile, support
from utils.texts import BOT_DESCRIPTION, BOT_SHORT_DESCRIPTION

# Analytics system — project root is already in sys.path
from analytics_startup import startup_analytics
from daily_reporter import send_daily_report, send_weekly_summary, ADMIN_CHAT_ID
from analytics_db import DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

API_PORT = int(os.getenv("API_PORT", "8000"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")


async def run_bot() -> None:
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Initialise analytics tables (safe no-op if they already exist)
    await startup_analytics(bot=bot, admin_chat_id=ADMIN_CHAT_ID)

    # Set description visible before /start and in "About" section
    try:
        await bot.set_my_description(description=BOT_DESCRIPTION, language_code="ru")
        logger.info("Bot description set (%d chars).", len(BOT_DESCRIPTION))
    except Exception as e:
        logger.warning("Could not set description: %s", e)
    try:
        await bot.set_my_short_description(short_description=BOT_SHORT_DESCRIPTION, language_code="ru")
        logger.info("Bot short description set (%d chars).", len(BOT_SHORT_DESCRIPTION))
    except Exception as e:
        logger.warning("Could not set short description: %s", e)

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(resume.router)
    dp.include_router(cover_letter.router)
    dp.include_router(interview.router)
    dp.include_router(vacancy_analysis.router)
    dp.include_router(ai_assistant.router)
    dp.include_router(payment.router)
    dp.include_router(profile.router)
    dp.include_router(support.router)
    # Weekly digest — every Monday 10:00 Moscow time (UTC+3 = 07:00 UTC)
    scheduler = AsyncIOScheduler()
    from services.digest import send_weekly_digest
    scheduler.add_job(
        send_weekly_digest,
        CronTrigger(day_of_week='mon', hour=7, minute=0),
        args=[bot],
        id='weekly_digest',
        replace_existing=True,
    )
    # Daily analytics report — every day at 08:00 Moscow (05:00 UTC)
    scheduler.add_job(
        lambda: asyncio.create_task(send_daily_report(bot, ADMIN_CHAT_ID, DB_PATH)),
        CronTrigger(hour=5, minute=0),
        id='daily_report',
        replace_existing=True,
    )
    # Weekly analytics summary — Monday 07:05 UTC (right after existing digest at 07:00)
    scheduler.add_job(
        lambda: asyncio.create_task(send_weekly_summary(bot, ADMIN_CHAT_ID, DB_PATH)),
        CronTrigger(day_of_week='mon', hour=7, minute=5),
        id='weekly_summary',
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Weekly digest scheduler started (Mon 10:00 MSK).")

    logger.info("Bot started.")
    await dp.start_polling(bot)


async def run_api() -> None:
    config = uvicorn.Config(
        "api.server:app",
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        reload=False,
    )
    server = uvicorn.Server(config)
    logger.info("API server starting on %s:%s …", API_HOST, API_PORT)
    await server.serve()


async def main() -> None:
    await init_db()
    logger.info("Database initialised.")
    await asyncio.gather(run_bot(), run_api())


if __name__ == "__main__":
    asyncio.run(main())
