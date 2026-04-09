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
from maintenance import is_maintenance, broadcast_maintenance_end

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

    # ── Global error middleware ───────────────────────────────────────────────
    # Catches any unhandled exception in a handler.
    # Shows user a friendly message instead of silence.
    # Notifies admin with traceback.
    @dp.errors()
    async def global_error_handler(event, exception):
        import traceback as _tb
        tb_text = _tb.format_exc()[-600:]
        logger.error("Unhandled exception: %s\n%s", exception, tb_text)

        # Try to reply to user with a friendly message
        try:
            update = event.update
            chat_id = None
            if update.message:
                chat_id = update.message.chat.id
            elif update.callback_query:
                chat_id = update.callback_query.message.chat.id
                try:
                    await update.callback_query.answer()
                except Exception:
                    pass

            if chat_id:
                await bot.send_message(
                    chat_id,
                    "⚙️ <b>Временный сбой</b>\n\n"
                    "Что-то пошло не так на нашем сервере. "
                    "Мы уже в курсе и чиним!\n\n"
                    "Попробуйте через несколько минут 🙏",
                    parse_mode="HTML",
                )
        except Exception as notify_err:
            logger.warning("Could not notify user about error: %s", notify_err)

        # Alert admin
        try:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"🐛 <b>Bot error</b>\n<pre>{tb_text}</pre>",
                parse_mode="HTML",
            )
        except Exception:
            pass

        return True  # mark as handled so aiogram doesn't re-raise

    # ── Maintenance mode middleware ───────────────────────────────────────────
    # If MAINTENANCE=1 is set in .env, all messages/callbacks get a
    # "we're fixing it" reply instead of normal processing.
    @dp.update.middleware()
    async def maintenance_middleware(handler, event, data):
        if not is_maintenance():
            return await handler(event, data)

        # Admin can still use the bot during maintenance
        user_id = None
        try:
            upd = event.update if hasattr(event, "update") else event
            if upd.message:
                user_id = upd.message.from_user.id
            elif upd.callback_query:
                user_id = upd.callback_query.from_user.id
                try:
                    await upd.callback_query.answer()
                except Exception:
                    pass
        except Exception:
            pass

        if user_id == ADMIN_CHAT_ID:
            return await handler(event, data)

        # Send maintenance message to regular user
        try:
            if hasattr(event, "update"):
                upd = event.update
                chat_id = None
                if upd.message:
                    chat_id = upd.message.chat.id
                elif upd.callback_query:
                    chat_id = upd.callback_query.message.chat.id
                if chat_id:
                    await bot.send_message(
                        chat_id,
                        "⚙️ <b>Технические работы</b>\n\n"
                        "На сервере временный сбой — мы уже чиним.\n"
                        "Все ваши данные в безопасности.\n\n"
                        "Бот вернётся в работу совсем скоро! 🙏",
                        parse_mode="HTML",
                    )
        except Exception:
            pass

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
    # Daily DB backup — every day at 03:00 UTC
    from backup import run_backup
    scheduler.add_job(
        lambda: asyncio.create_task(run_backup()),
        CronTrigger(hour=3, minute=0),
        id='daily_backup',
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
