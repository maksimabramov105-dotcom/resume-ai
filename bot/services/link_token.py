"""
link_token.py — Issue signed one-time link tokens for the Telegram→AutoApply SSO flow.

The bot calls issue_link_token(); the AutoApply API verifies with the same secret.
Algorithm: HMAC-SHA256 over base64url(json_payload).
TTL: 5 minutes.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

_LINK_TTL = 300  # seconds
_LINK_SECRET: str = os.getenv("LINK_SECRET", "")


def issue_link_token(telegram_id: int) -> str:
    """
    Issue a signed one-time token for `telegram_id`.
    Raises ValueError if LINK_SECRET env var is not set.
    """
    secret = _LINK_SECRET
    if not secret:
        raise ValueError("LINK_SECRET is not configured")

    jti = secrets.token_urlsafe(16)
    exp = int(time.time()) + _LINK_TTL
    payload_json = json.dumps(
        {"tid": telegram_id, "jti": jti, "exp": exp}, separators=(",", ":")
    )
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    sig = hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"
