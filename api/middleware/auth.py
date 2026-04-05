import hashlib
import hmac
import json
import os
from urllib.parse import parse_qs
from fastapi import Request, HTTPException

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


def validate_init_data(init_data: str) -> dict:
    """
    Validates Telegram Mini App initData signature.
    Returns parsed user dict if valid, raises 401 otherwise.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram init data")

    parsed = {}
    for k, v in parse_qs(init_data, keep_blank_values=True).items():
        parsed[k] = v[0] if len(v) == 1 else v

    if "hash" not in parsed:
        raise HTTPException(status_code=401, detail="Missing hash in init data")

    received_hash = parsed.pop("hash")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    secret_key = hmac.new(
        b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256
    ).digest()

    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if calculated_hash != received_hash:
        raise HTTPException(status_code=401, detail="Invalid Telegram signature")

    user_data = json.loads(parsed.get("user", "{}"))
    return user_data


async def get_telegram_user(request: Request) -> dict:
    """FastAPI dependency — extracts and validates Telegram user from request headers."""
    # Dev mode: allow fake user for local testing without Telegram
    if DEV_MODE:
        fake_id = request.headers.get("X-Dev-User-Id", "123456789")
        return {
            "id": int(fake_id),
            "first_name": "Dev",
            "last_name": "User",
            "username": "devuser",
        }

    init_data = request.headers.get("X-Telegram-Init-Data", "")
    return validate_init_data(init_data)
