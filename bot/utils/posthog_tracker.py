"""PostHog analytics for the Telegram bot. Never raises — analytics must not crash the bot."""
import os
from posthog import Posthog

_PH_KEY = os.getenv("POSTHOG_API_KEY", "")

ph = Posthog(project_api_key=_PH_KEY, host="https://us.i.posthog.com")


def track(user_id: int, event: str, properties: dict | None = None) -> None:
    try:
        ph.capture(str(user_id), event, properties or {})
    except Exception:
        pass


def identify(user_id: int, properties: dict) -> None:
    try:
        ph.identify(str(user_id), properties)
    except Exception:
        pass
