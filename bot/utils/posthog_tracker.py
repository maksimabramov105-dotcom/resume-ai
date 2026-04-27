"""PostHog analytics for the Telegram bot. Never raises — analytics must not crash the bot."""
from bot.analytics import track, identify  # noqa: F401
