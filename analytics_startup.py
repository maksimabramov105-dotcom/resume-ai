"""
analytics_startup.py — One-time initialisation called on bot startup.

Ensures the four analytics tables exist in the database before any
tracking calls are made. Safe to call every time — uses IF NOT EXISTS.
Never raises — wraps everything in try/except.

INTEGRATION INSTRUCTIONS:
─────────────────────────────────────────────────────────────────────
In run.py, inside the main() async function, add TWO lines:

    1. Import at the top of run.py:
       from analytics_startup import startup_analytics

    2. Call inside main(), AFTER await init_db():
       await startup_analytics(bot, ADMIN_CHAT_ID)

Full example in run.py main():

    async def main() -> None:
        await init_db()
        logger.info("Database initialised.")

        from analytics_startup import startup_analytics
        from daily_reporter import ADMIN_CHAT_ID
        # bot is not available yet here, pass None — startup_analytics handles it
        await startup_analytics(admin_chat_id=ADMIN_CHAT_ID)

        await asyncio.gather(run_bot(), run_api())

OR — call it inside run_bot() after the bot object is created:

    async def run_bot() -> None:
        bot = Bot(token=BOT_TOKEN, ...)
        from analytics_startup import startup_analytics
        from daily_reporter import ADMIN_CHAT_ID
        await startup_analytics(admin_chat_id=ADMIN_CHAT_ID)
        ...
─────────────────────────────────────────────────────────────────────
"""

import logging
import sys
import os

logger = logging.getLogger(__name__)

# Make sure project root is on path so analytics_db can be imported
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


async def startup_analytics(bot=None, admin_chat_id: int = None) -> None:
    """
    Initialises analytics tables. Called once on bot startup.

    Parameters:
      bot            — aiogram Bot instance (optional, used for future startup alerts)
      admin_chat_id  — admin Telegram ID (optional, for startup alerts)

    Never raises — all errors are caught and logged as warnings.
    """
    try:
        from analytics_db import init_analytics_db, DB_PATH
        await init_analytics_db(DB_PATH)
        logger.info("✅ Analytics DB initialized at %s", DB_PATH)
    except Exception as e:
        logger.warning("⚠️ Analytics DB init failed (non-fatal): %s", e)
