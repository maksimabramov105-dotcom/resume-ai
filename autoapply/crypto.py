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
