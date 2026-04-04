import asyncio
import logging
import sys
import os

# Add bot/ directory to path so all imports work as flat modules
sys.path.insert(0, os.path.dirname(__file__))

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database.db import init_db
from handlers import start, resume, cover_letter, interview, vacancy_analysis, ai_assistant, payment, profile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    await init_db()
    logger.info("Database initialized.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Order matters — more specific routers first
    dp.include_router(start.router)
    dp.include_router(resume.router)
    dp.include_router(cover_letter.router)
    dp.include_router(interview.router)
    dp.include_router(vacancy_analysis.router)
    dp.include_router(ai_assistant.router)
    dp.include_router(payment.router)
    dp.include_router(profile.router)

    logger.info("Bot started.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
