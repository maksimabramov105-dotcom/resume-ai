"""
autoapply/services/referral.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Signed referral-code generation, validation, and conversion tracking.

Flow
----
1. User A calls ``generate_code(user_id)`` and shares the resulting link.
2. New user B registers with that code; the API calls ``apply_referral``.
3. When B pays for a plan, the payment handler calls ``mark_converted``.
4. The dashboard calls ``get_referral_stats`` to show A their referral counts.

Schema (created by ``_MIGRATE_REFERRALS``)
------------------------------------------
referrals(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id  INTEGER NOT NULL,
    new_user_id  INTEGER UNIQUE NOT NULL,
    created_at   TEXT NOT NULL,
    converted_at TEXT            -- NULL until the referred user pays
)

No external dependencies — only stdlib + aiosqlite.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Migration DDL
# ---------------------------------------------------------------------------

_MIGRATE_REFERRALS = """
CREATE TABLE IF NOT EXISTS referrals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id  INTEGER NOT NULL,
    new_user_id  INTEGER UNIQUE NOT NULL,
    created_at   TEXT    NOT NULL,
    converted_at TEXT
)
"""


# ---------------------------------------------------------------------------
# Public helpers — synchronous, no DB access
# ---------------------------------------------------------------------------

def generate_code(user_id: int) -> str:
    """Return a signed referral code for *user_id*.

    Format: ``<b32_payload><4-char-checksum>``

    The payload is the 4-byte big-endian representation of *user_id*
    base32-encoded (lowercase, padding stripped).  The checksum is the
    first 4 hex characters of ``SHA-256(payload)``.

    Parameters
    ----------
    user_id:
        Positive integer user identifier (must fit in 4 bytes, i.e. ≤ 2^32-1).

    Returns
    -------
    str
        A short, URL-safe referral code, e.g. ``"aebagba"`` + ``"3f2a"``.

    Examples
    --------
    >>> code = generate_code(42)
    >>> len(code) > 4
    True
    >>> validate_code(code) == 42
    True
    """
    payload = (
        base64.b32encode(user_id.to_bytes(4, "big"))
        .decode()
        .rstrip("=")
        .lower()
    )
    checksum = hashlib.sha256(payload.encode()).hexdigest()[:4]
    return payload + checksum


def validate_code(code: str) -> Optional[int]:
    """Validate a referral code and return the embedded user_id.

    Splits off the last 4 characters as the checksum, re-derives the
    expected checksum from the remaining payload, and returns the decoded
    ``user_id`` on match or ``None`` on any mismatch / malformed input.

    Parameters
    ----------
    code:
        A referral code previously produced by :func:`generate_code`.

    Returns
    -------
    int or None
        The original ``user_id`` if the code is authentic, ``None`` otherwise.

    Examples
    --------
    >>> validate_code("invalid") is None
    True
    """
    if not code or len(code) < 5:
        return None

    payload, checksum = code[:-4], code[-4:]
    expected = hashlib.sha256(payload.encode()).hexdigest()[:4]
    if checksum != expected:
        logger.debug("[referral] checksum mismatch for code prefix=%s", payload)
        return None

    try:
        # Re-pad to a multiple of 8 characters required by base32
        padding = (8 - len(payload) % 8) % 8
        padded = (payload + "=" * padding).upper()
        raw = base64.b32decode(padded)
        return int.from_bytes(raw, "big")
    except Exception as exc:  # noqa: BLE001
        logger.debug("[referral] decode error: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Async DB helpers
# ---------------------------------------------------------------------------

async def apply_referral(
    referrer_id: int,
    new_user_id: int,
    db_path: str,
) -> bool:
    """Record that *new_user_id* signed up via *referrer_id*'s referral link.

    Inserts a new row into ``referrals`` with ``converted_at = NULL``.
    The ``new_user_id`` column has a UNIQUE constraint, so a duplicate
    registration attempt returns ``False`` without raising.

    Also runs ``_MIGRATE_REFERRALS`` to ensure the table exists.

    Parameters
    ----------
    referrer_id:
        ``autoapply_users.id`` of the user who shared the referral link.
    new_user_id:
        ``autoapply_users.id`` of the newly registered user.
    db_path:
        Filesystem path to the aiosqlite database file.

    Returns
    -------
    bool
        ``True`` on a successful insert, ``False`` if the row already exists
        or any other error occurs.
    """
    now = datetime.now(timezone.utc).isoformat()
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(_MIGRATE_REFERRALS)
            await db.execute(
                """
                INSERT INTO referrals (referrer_id, new_user_id, created_at)
                VALUES (?, ?, ?)
                """,
                (referrer_id, new_user_id, now),
            )
            await db.commit()
        logger.info(
            "[referral] applied referral referrer=%d new_user=%d",
            referrer_id,
            new_user_id,
        )
        return True
    except aiosqlite.IntegrityError:
        logger.debug(
            "[referral] duplicate referral for new_user_id=%d", new_user_id
        )
        return False
    except Exception as exc:  # noqa: BLE001
        logger.exception("[referral] apply_referral error: %s", exc)
        return False


async def mark_converted(new_user_id: int, db_path: str) -> Optional[int]:
    """Mark a referred user's referral as converted (they paid).

    Sets ``converted_at`` to the current UTC timestamp for the row where
    ``new_user_id`` matches.  Also runs the migration DDL so the table is
    guaranteed to exist before querying.

    Parameters
    ----------
    new_user_id:
        ``autoapply_users.id`` of the user who just completed a payment.
    db_path:
        Filesystem path to the aiosqlite database file.

    Returns
    -------
    int or None
        The ``referrer_id`` whose referral was converted, or ``None`` if
        *new_user_id* has no referral record or the row was already converted.

    Notes
    -----
    Callers should credit the referrer with a free month when this returns a
    non-``None`` value.
    """
    now = datetime.now(timezone.utc).isoformat()
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(_MIGRATE_REFERRALS)
            # Only convert once (converted_at IS NULL guard)
            cursor = await db.execute(
                """
                UPDATE referrals
                SET    converted_at = ?
                WHERE  new_user_id = ?
                  AND  converted_at IS NULL
                RETURNING referrer_id
                """,
                (now, new_user_id),
            )
            row = await cursor.fetchone()
            await db.commit()

        if row:
            referrer_id: int = row[0]
            logger.info(
                "[referral] converted new_user=%d referrer=%d",
                new_user_id,
                referrer_id,
            )
            return referrer_id

        logger.debug(
            "[referral] mark_converted: no pending referral for new_user_id=%d",
            new_user_id,
        )
        return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("[referral] mark_converted error: %s", exc)
        return None


async def get_referral_stats(user_id: int, db_path: str) -> dict:
    """Return referral statistics for *user_id* as a dict.

    Parameters
    ----------
    user_id:
        ``autoapply_users.id`` of the referrer.
    db_path:
        Filesystem path to the aiosqlite database file.

    Returns
    -------
    dict
        ``{"invited": N, "converted": N, "pending": N}`` where:

        * ``invited``   — total rows where ``referrer_id = user_id``.
        * ``converted`` — rows where ``converted_at IS NOT NULL``.
        * ``pending``   — rows where ``converted_at IS NULL``.

    Examples
    --------
    >>> import asyncio
    >>> stats = asyncio.run(get_referral_stats(1, "/tmp/test.db"))
    >>> set(stats.keys()) == {"invited", "converted", "pending"}
    True
    """
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(_MIGRATE_REFERRALS)
            cursor = await db.execute(
                """
                SELECT
                    COUNT(*)                                      AS invited,
                    COUNT(CASE WHEN converted_at IS NOT NULL THEN 1 END) AS converted,
                    COUNT(CASE WHEN converted_at IS NULL     THEN 1 END) AS pending
                FROM referrals
                WHERE referrer_id = ?
                """,
                (user_id,),
            )
            row = await cursor.fetchone()

        if row:
            return {"invited": row[0], "converted": row[1], "pending": row[2]}
        return {"invited": 0, "converted": 0, "pending": 0}
    except Exception as exc:  # noqa: BLE001
        logger.exception("[referral] get_referral_stats error: %s", exc)
        return {"invited": 0, "converted": 0, "pending": 0}
