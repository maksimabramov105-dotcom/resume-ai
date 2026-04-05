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

from config import BOT_TOKEN  # flat import (bot/ is in sys.path)
from database.db import init_db
from handlers import start, resume, cover_letter, interview, vacancy_analysis, ai_assistant, payment, profile, support
from utils.texts import BOT_DESCRIPTION, BOT_SHORT_DESCRIPTION

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
