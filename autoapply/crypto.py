"""
crypto.py — Symmetric encryption for sensitive AutoApply fields.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` package.
Key source: ENCRYPTION_KEY env var (base64-urlsafe 32-byte Fernet key).

Generate a new key:
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

If ENCRYPTION_KEY is not set, encrypt() returns the plaintext unchanged and
decrypt() returns the stored value unchanged — safe degraded mode for dev/test
but logs a warning so it's obvious encryption is off.
"""
import base64
import logging
import os

logger = logging.getLogger(__name__)

_KEY_RAW = os.getenv("ENCRYPTION_KEY", "")
_fernet = None

if _KEY_RAW:
    try:
        from cryptography.fernet import Fernet, InvalidToken
        _fernet = Fernet(_KEY_RAW.encode() if isinstance(_KEY_RAW, str) else _KEY_RAW)
        logger.debug("[crypto] Fernet encryption initialised")
    except Exception as _e:
        logger.error("[crypto] Failed to initialise Fernet (bad ENCRYPTION_KEY?): %s", _e)
        _fernet = None
else:
    logger.warning("[crypto] ENCRYPTION_KEY not set — sensitive fields stored in plaintext")


def encrypt(plaintext: str) -> str:
    """
    Encrypt a string. Returns a Fernet token (URL-safe base64 string).
    Returns plaintext unchanged if ENCRYPTION_KEY is not set.
    """
    if not plaintext:
        return plaintext
    if _fernet is None:
        return plaintext
    try:
        return _fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")
    except Exception as exc:
        logger.error("[crypto] encrypt error: %s", exc)
        return plaintext  # fail open rather than lose data


def decrypt(token: str) -> str:
    """
    Decrypt a Fernet token. Returns the original plaintext.
    Returns the token unchanged if:
      - ENCRYPTION_KEY is not set (stored plaintext)
      - The token is not a valid Fernet token (stored plaintext from before encryption was enabled)
    Never raises — logs warning and returns '' on unrecoverable error.
    """
    if not token:
        return token
    if _fernet is None:
        return token
    try:
        from cryptography.fernet import InvalidToken
        return _fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except Exception:
        # Likely stored plaintext (pre-encryption migration) — return as-is
        logger.debug("[crypto] decrypt: value is not a Fernet token, returning raw")
        return token


def is_encrypted(value: str) -> bool:
    """Heuristic: Fernet tokens start with 'gAAAAA' (version byte 0x80)."""
    return bool(value) and value.startswith("gAAAAA")


# ── Telegram link tokens (HMAC-SHA256, 5-min TTL) ────────────────────────────
#
# Format: base64url(json_payload) + "." + hex(hmac_sha256)
# Payload: {"tid": telegram_id, "jti": unique_id, "exp": unix_timestamp}
#
# The bot calls issue_link_token(); the AutoApply API calls verify_link_token().
# One-time enforcement is done in autoapply_db (used_link_jti table).

import hashlib
import hmac as _hmac
import json
import secrets
import time
from typing import Optional


_LINK_TTL = 300  # 5 minutes


def issue_link_token(telegram_id: int, secret: str) -> str:
    """Issue a signed one-time link token for a Telegram user."""
    if not secret:
        raise ValueError("LINK_SECRET is not set — cannot issue link tokens")
    jti = secrets.token_urlsafe(16)
    exp = int(time.time()) + _LINK_TTL
    payload_json = json.dumps({"tid": telegram_id, "jti": jti, "exp": exp}, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    sig = _hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_link_token(token: str, secret: str) -> Optional[dict]:
    """
    Verify a link token. Returns the payload dict on success, None on failure.

    Does NOT check one-time use — that is the caller's responsibility.
    """
    if not secret or not token or "." not in token:
        return None
    try:
        payload_b64, received_sig = token.rsplit(".", 1)
        expected_sig = _hmac.new(secret.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not _hmac.compare_digest(expected_sig, received_sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        if int(time.time()) > payload["exp"]:
            return None  # expired
        return payload
    except Exception:
        return None
