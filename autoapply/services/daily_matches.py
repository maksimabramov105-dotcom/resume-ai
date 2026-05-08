"""
autoapply/services/daily_matches.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Daily job-match digest — designed to run at 07:00 UTC via APScheduler or a
cron job.

For each user who has at least one active campaign the service:
1. Finds candidate vacancies from ``vacancies_cache`` by keyword matching
   against the campaign ``job_title`` (used as the keyword source because the
   ``campaigns`` table has no separate ``keywords`` column).
2. De-duplicates hits across all of a user's campaigns.
3. Scores each vacancy with :func:`score_match` (pure keyword overlap, 0–10).
4. Takes the top-5 by score (tie-breaking by ``fetched_at`` recency).
5. Formats a short digest message.
6. Sends it via Telegram DM and, if the user has an email, via
   :mod:`autoapply.email_sender`.

No external AI calls are made — this is intentionally a lightweight,
infrastructure-only first version.

Telegram ``bot`` object
-----------------------
The ``bot`` parameter accepted by :func:`run_daily_matches` is assumed to
expose an async ``send_message(chat_id, text, parse_mode)`` coroutine
compatible with *python-telegram-bot* v20 / *aiogram* v3.  If neither is
available in the current environment the :func:`_send_telegram` helper will
catch any exception and return ``False``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal DB helpers
# ---------------------------------------------------------------------------

async def _get_active_users_with_campaigns(db_path: str) -> list[dict]:
    """Return users who have at least one active campaign.

    Each returned dict contains the joined columns from ``autoapply_users``
    and the matching campaign rows (one dict per campaign).

    The query performs a JOIN so that every returned row is one
    (user, campaign) pair.  The caller groups by user as needed.

    Parameters
    ----------
    db_path:
        Filesystem path to the aiosqlite database file.

    Returns
    -------
    list[dict]
        List of dicts with keys: ``user_id``, ``telegram_id``, ``email``,
        ``lang`` (defaulting to ``'en'`` if the column is absent),
        ``campaign_id``, ``job_title``, ``engine``.
    """
    sql = """
        SELECT
            u.id           AS user_id,
            u.telegram_id  AS telegram_id,
            u.email        AS email,
            c.id           AS campaign_id,
            c.job_title    AS job_title,
            COALESCE(c.engine, 'api_boards') AS engine
        FROM autoapply_users AS u
        JOIN campaigns AS c
          ON c.user_id = u.id
         AND c.status  = 'active'
        ORDER BY u.id, c.id
    """
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql)
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:  # noqa: BLE001
        logger.exception("[daily_matches] _get_active_users_with_campaigns error: %s", exc)
        return []


async def _fetch_vacancies_for_keyword(
    keyword: str,
    db_path: str,
    limit: int = 50,
) -> list[dict]:
    """Return vacancies from ``vacancies_cache`` that mention *keyword*.

    Matches against both ``title`` and ``description`` columns using SQLite
    LIKE (case-insensitive by default for ASCII text).

    Parameters
    ----------
    keyword:
        A word or short phrase, e.g. ``"python developer"``.
    db_path:
        Filesystem path to the aiosqlite database file.
    limit:
        Maximum rows to return per keyword (default 50).

    Returns
    -------
    list[dict]
        Vacancy dicts with keys: ``id``, ``vacancy_id``, ``title``,
        ``company``, ``location``, ``salary``, ``description``, ``url``,
        ``fetched_at``.
    """
    pattern = f"%{keyword}%"
    sql = """
        SELECT id, vacancy_id, title, company, location, salary,
               description, url, fetched_at
        FROM   vacancies_cache
        WHERE  (title       LIKE ? OR description LIKE ?)
        ORDER  BY fetched_at DESC
        LIMIT  ?
    """
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, (pattern, pattern, limit))
            rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "[daily_matches] _fetch_vacancies_for_keyword error (kw=%s): %s",
            keyword, exc,
        )
        return []


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_match(vacancy: dict, campaign: dict) -> float:
    """Return a keyword-overlap score between *vacancy* and *campaign*.

    Splits the campaign ``job_title`` on whitespace to derive keywords, then
    counts how many of those keywords appear (case-insensitive) in the
    concatenation of the vacancy ``title`` and ``description``.  The raw hit
    count is normalised to a 0–10 scale based on the total keyword count.

    Parameters
    ----------
    vacancy:
        Dict with at least ``title`` (str) and ``description`` (str or None).
    campaign:
        Dict with at least ``job_title`` (str).

    Returns
    -------
    float
        Score in [0.0, 10.0].  Returns ``0.0`` if there are no keywords.

    Examples
    --------
    >>> v = {"title": "Python Developer", "description": "Django, REST, Docker"}
    >>> c = {"job_title": "Python Developer Django"}
    >>> score_match(v, c)
    10.0
    """
    keywords: list[str] = [
        kw.lower()
        for kw in (campaign.get("job_title") or "").split()
        if len(kw) > 1
    ]
    if not keywords:
        return 0.0

    haystack = " ".join([
        (vacancy.get("title") or ""),
        (vacancy.get("description") or ""),
    ]).lower()

    hits = sum(1 for kw in keywords if kw in haystack)
    return round(min(hits / len(keywords), 1.0) * 10, 2)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _format_digest(user_lang: str, matches: list[dict]) -> str:
    """Build a Telegram-formatted digest message.

    Parameters
    ----------
    user_lang:
        ISO 639-1 language code; ``'ru'`` for Russian, anything else → English.
    matches:
        Ordered list of vacancy dicts, each containing at minimum ``title``,
        ``company``, ``url``, and ``score`` (float).

    Returns
    -------
    str
        A multi-line string ready to be sent via Telegram with
        ``parse_mode='Markdown'``.
    """
    if user_lang == "ru":
        header = "☀️ Ваши 5 лучших вакансий сегодня:\n"
        score_label = "оценка"
    else:
        header = "☀️ Your 5 best matches today:\n"
        score_label = "score"

    lines: list[str] = [header]
    for i, v in enumerate(matches[:5], start=1):
        title   = v.get("title")   or "—"
        company = v.get("company") or "—"
        url     = v.get("url")     or ""
        score   = v.get("score", 0.0)
        lines.append(
            f"{i}. **{title}** @ {company}\n"
            f"   {score_label}: {score}/10"
            + (f" · {url}" if url else "")
        )

    return "\n\n".join(lines) if len(lines) > 1 else header


# ---------------------------------------------------------------------------
# Delivery helpers
# ---------------------------------------------------------------------------

async def _send_telegram(bot: Any, telegram_id: int, text: str) -> bool:
    """Send *text* to *telegram_id* via the supplied bot instance.

    Attempts to call ``bot.send_message(chat_id=telegram_id, text=text,
    parse_mode='Markdown')``.  Both coroutine and non-coroutine callables
    are handled (the result is awaited only if it is a coroutine).

    Parameters
    ----------
    bot:
        A bot object with a ``send_message`` method (python-telegram-bot v20+,
        aiogram v3, or any compatible wrapper).
    telegram_id:
        The Telegram user/chat identifier.
    text:
        Message text, may contain Markdown formatting.

    Returns
    -------
    bool
        ``True`` if the message was sent without exception, ``False`` otherwise.
    """
    try:
        result = bot.send_message(
            chat_id=telegram_id,
            text=text,
            parse_mode="Markdown",
        )
        if asyncio.iscoroutine(result):
            await result
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[daily_matches] Telegram send failed for %d: %s", telegram_id, exc
        )
        return False


async def _send_email(email: str, digest_html: str) -> bool:
    """Send the digest to *email* via :mod:`autoapply.email_sender`.

    Imports ``autoapply.email_sender.send_digest_email`` (or falls back to
    ``send_welcome_email`` if the digest-specific function is absent) at
    call-time so that the module can be imported in environments where the
    email sender is not configured.

    Parameters
    ----------
    email:
        Recipient e-mail address.
    digest_html:
        HTML body of the digest.

    Returns
    -------
    bool
        ``True`` if the email was dispatched without exception, ``False`` on
        any error (import failure, SMTP error, etc.).
    """
    try:
        from autoapply import email_sender  # local import to stay testable

        # Prefer a dedicated digest sender; fall back to the generic _send.
        sender_fn = getattr(email_sender, "send_digest_email", None)
        if sender_fn is None:
            sender_fn = getattr(email_sender, "_send", None)
        if sender_fn is None:
            logger.warning("[daily_matches] email_sender has no suitable send function")
            return False

        result = sender_fn(
            email,
            subject="Your daily job matches",
            html=digest_html,
            text=digest_html,  # plain-text fallback is fine for now
        )
        # _send / send_digest_email may be sync or async
        if asyncio.iscoroutine(result):
            result = await result
        return bool(result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[daily_matches] email send failed for %s: %s", email, exc)
        return False


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_daily_matches(bot: Any, db_path: str) -> int:
    """Generate and send the daily job-match digest to all eligible users.

    Iterates over every user with at least one active campaign, builds a
    top-5 vacancy digest per user, and delivers it via Telegram DM and
    (optionally) email.

    Parameters
    ----------
    bot:
        An initialised Telegram bot instance; passed directly to
        :func:`_send_telegram`.
    db_path:
        Filesystem path to the aiosqlite database.

    Returns
    -------
    int
        The number of users who received at least one successful notification.

    Notes
    -----
    * The function is designed to be called by APScheduler or a cron trigger
      at 07:00 UTC.
    * Users without a ``telegram_id`` who also lack an email address are
      silently skipped.
    * Vacancy de-duplication across campaigns uses the ``vacancy_id`` column.
    """
    logger.info("[daily_matches] run started at %s", datetime.now(timezone.utc).isoformat())

    rows = await _get_active_users_with_campaigns(db_path)
    if not rows:
        logger.info("[daily_matches] no active users with campaigns, exiting")
        return 0

    # Group campaigns by user
    from collections import defaultdict
    users: dict[int, dict] = {}
    user_campaigns: dict[int, list[dict]] = defaultdict(list)

    for row in rows:
        uid = row["user_id"]
        if uid not in users:
            users[uid] = {
                "user_id":     uid,
                "telegram_id": row["telegram_id"],
                "email":       row["email"],
                # The schema has no lang column; default to 'en'.
                "lang":        row.get("lang", "en") or "en",
            }
        user_campaigns[uid].append({
            "campaign_id": row["campaign_id"],
            "job_title":   row["job_title"],
            "engine":      row["engine"],
        })

    notified = 0

    for uid, user in users.items():
        campaigns = user_campaigns[uid]

        # Collect vacancies across all campaigns; deduplicate by vacancy_id
        seen_ids: set[str] = set()
        scored: list[dict] = []

        for campaign in campaigns:
            keyword = campaign.get("job_title") or ""
            if not keyword.strip():
                continue

            vacancies = await _fetch_vacancies_for_keyword(keyword, db_path)
            for vac in vacancies:
                vid = str(vac.get("vacancy_id") or vac.get("id") or "")
                if vid and vid in seen_ids:
                    continue
                seen_ids.add(vid)

                vac["score"] = score_match(vac, campaign)
                scored.append(vac)

        if not scored:
            logger.debug("[daily_matches] no vacancies for user_id=%d", uid)
            continue

        # Sort by score desc, then by fetched_at desc as tie-breaker
        scored.sort(
            key=lambda v: (v["score"], v.get("fetched_at") or ""),
            reverse=True,
        )
        top5 = scored[:5]

        lang    = user.get("lang", "en")
        message = _format_digest(lang, top5)

        user_notified = False

        # --- Telegram ---
        tg_id = user.get("telegram_id")
        if tg_id:
            ok = await _send_telegram(bot, tg_id, message)
            if ok:
                user_notified = True
                logger.info("[daily_matches] Telegram digest sent to user_id=%d", uid)

        # --- Email ---
        email = user.get("email")
        if email:
            # Convert Markdown bold (**text**) to HTML <b>text</b> for email
            digest_html = message.replace("**", "<b>", 1)
            while "**" in digest_html:
                digest_html = digest_html.replace("**", "</b>", 1)
                digest_html = digest_html.replace("**", "<b>", 1)
            ok = await _send_email(email, f"<pre>{digest_html}</pre>")
            if ok:
                user_notified = True
                logger.info("[daily_matches] email digest sent to user_id=%d", uid)

        if user_notified:
            notified += 1

    logger.info("[daily_matches] run complete — notified %d users", notified)
    return notified


# ---------------------------------------------------------------------------
# Dry-run / manual test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.DEBUG)

    # Locate the database next to this file's project root (adjust if needed)
    _here = os.path.dirname(os.path.abspath(__file__))
    _db   = os.environ.get(
        "AUTOAPPLY_DB",
        os.path.join(_here, "..", "..", "autoapply.db"),
    )

    async def _dry_run() -> None:
        """Print the digest for a fixture user (user_id=1) without sending."""
        print(f"[dry-run] database: {_db}")

        rows = await _get_active_users_with_campaigns(_db)
        fixture_uid = 1

        # Collect campaigns for fixture user
        campaigns = [r for r in rows if r["user_id"] == fixture_uid]
        if not campaigns:
            print(f"[dry-run] user_id={fixture_uid} has no active campaigns.")
            # Show a synthetic example instead
            sample_vacancy = {
                "title":       "Python Developer",
                "company":     "ACME Corp",
                "url":         "https://example.com/jobs/1",
                "description": "We need a Python developer with Django and Docker.",
                "fetched_at":  "2026-05-08T06:00:00",
                "score":       0.0,
            }
            sample_campaign = {"job_title": "Python Developer"}
            sample_vacancy["score"] = score_match(sample_vacancy, sample_campaign)
            digest = _format_digest("en", [sample_vacancy])
            print("\n--- Synthetic digest (EN) ---")
            print(digest)
            digest_ru = _format_digest("ru", [sample_vacancy])
            print("\n--- Synthetic digest (RU) ---")
            print(digest_ru)
            return

        seen_ids: set[str] = set()
        scored: list[dict] = []
        for row in campaigns:
            campaign = {"job_title": row["job_title"]}
            vacs = await _fetch_vacancies_for_keyword(row["job_title"], _db)
            for v in vacs:
                vid = str(v.get("vacancy_id") or v.get("id") or "")
                if vid and vid in seen_ids:
                    continue
                seen_ids.add(vid)
                v["score"] = score_match(v, campaign)
                scored.append(v)

        scored.sort(key=lambda v: (v["score"], v.get("fetched_at") or ""), reverse=True)
        top5 = scored[:5]

        digest = _format_digest("en", top5)
        print(f"\n--- Digest for user_id={fixture_uid} (EN) ---")
        print(digest)

    asyncio.run(_dry_run())
