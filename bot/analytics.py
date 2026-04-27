import os
from posthog import Posthog

ph = Posthog(
    project_api_key=os.getenv('POSTHOG_API_KEY', ''),
    host='https://us.i.posthog.com'
)


def track(user_id: int, event: str, properties: dict = None):
    """Fire a PostHog event. Never raises — analytics must not break the bot."""
    try:
        ph.capture(
            distinct_id=str(user_id),
            event=event,
            properties=properties or {}
        )
    except Exception:
        pass


def identify(user_id: int, properties: dict):
    """Set persistent user properties in PostHog."""
    try:
        ph.identify(
            distinct_id=str(user_id),
            properties=properties
        )
    except Exception:
        pass
