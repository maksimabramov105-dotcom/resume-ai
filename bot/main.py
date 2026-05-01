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
from aiogram.types import ErrorEvent

from config import BOT_TOKEN
from database.db import init_db
from handlers import start, resume, cover_letter, interview, vacancy_analysis, ai_assistant, payment, profile, support, checkin, language, tracker
from handlers.checkin import checkin_loop
from utils.texts import BOT_DESCRIPTION, BOT_SHORT_DESCRIPTION

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Sentry (graceful no-op if SENTRY_DSN not set) ────────────────────────────
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    import sentry_sdk
    sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1)
    logger.info("Sentry initialised")


async def main():
    await init_db()
    logger.info("Database initialized.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Order matters — more specific routers first
    dp.include_router(language.router)  # must be first: handles lang:ru/lang:en from any screen
    dp.include_router(start.router)
    dp.include_router(resume.router)
    dp.include_router(cover_letter.router)
    dp.include_router(interview.router)
    dp.include_router(vacancy_analysis.router)
    dp.include_router(ai_assistant.router)
    dp.include_router(payment.router)
    dp.include_router(profile.router)
    dp.include_router(support.router)
    dp.include_router(checkin.router)
    dp.include_router(tracker.router)

    # Set bot description visible to users before pressing /start
    try:
        await bot.set_my_description(description=BOT_DESCRIPTION, language_code="ru")
        await bot.set_my_short_description(short_description=BOT_SHORT_DESCRIPTION, language_code="ru")
        logger.info("Bot description updated.")
    except Exception as e:
        logger.warning("Could not set bot description: %s", e)

    @dp.errors()
    async def global_error_handler(event: ErrorEvent) -> bool:
        logger.exception(
            "Unhandled bot error in update %s: %s",
            event.update.update_id if event.update else "?",
            event.exception,
            exc_info=event.exception,
        )
        if _sentry_dsn:
            import sentry_sdk
            sentry_sdk.capture_exception(event.exception)
        return True  # mark handled — prevents aiogram from re-raising

    logger.info("Bot started.")
    asyncio.create_task(checkin_loop(bot))  # T+24h onboarding check-in background task
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
