"""PostHog analytics for the Telegram bot. Never raises — analytics must not crash the bot."""
import os
import posthog

posthog.project_api_key = os.getenv("POSTHOG_API_KEY", "")
posthog.host = "https://us.i.posthog.com"
posthog.disabled = not os.getenv("POSTHOG_API_KEY", "")


def track(user_id: int, event: str, properties: dict | None = None) -> None:
    try:
        if posthog.project_api_key:
            posthog.capture(str(user_id), event, properties or {})
    except Exception:
        pass


def identify(user_id: int, properties: dict) -> None:
    try:
        if posthog.project_api_key:
            posthog.identify(str(user_id), properties)
    except Exception:
        pass
