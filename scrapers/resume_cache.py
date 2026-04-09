"""
resume_cache.py — Cache resume generation results to save API costs.
Reuses resumes for similar vacancies (same job title, different companies).
Cache stored in autoapply.db, expires after 7 days.
"""
import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

CACHE_TTL_DAYS = 7


async def init_cache_table(db_path: str) -> None:
    """
    CREATE TABLE IF NOT EXISTS resume_cache with columns:
    id, user_id, job_title_hash, vacancy_desc_hash, resume_text, created_at, hits
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS resume_cache (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL,
                job_title_hash   TEXT    NOT NULL,
                vacancy_desc_hash TEXT   NOT NULL,
                resume_text      TEXT    NOT NULL,
                created_at       TEXT    NOT NULL,
                hits             INTEGER DEFAULT 0
            )
        """)
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_resume_cache_user_title "
            "ON resume_cache (user_id, job_title_hash)"
        )
        await db.commit()
    logger.info("[resume_cache] Cache table initialized in %s", db_path)


def get_job_title_hash(job_title: str) -> str:
    """md5 of lowercase stripped job title."""
    normalized = job_title.lower().strip()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def get_vacancy_hash(vacancy_description: str) -> str:
    """md5 of first 500 chars of vacancy description."""
    snippet = vacancy_description[:500]
    return hashlib.md5(snippet.encode("utf-8")).hexdigest()


def texts_are_similar(desc1: str, desc2: str, threshold: float = 0.7) -> bool:
    """
    Jaccard similarity: count common words / total unique words.
    Returns True if similarity > threshold.
    """
    if not desc1 or not desc2:
        return False

    def tokenize(text: str) -> set:
        # Lowercase, split on whitespace/punctuation
        import re
        words = re.findall(r"\b\w+\b", text.lower())
        return set(words)

    words1 = tokenize(desc1)
    words2 = tokenize(desc2)

    if not words1 or not words2:
        return False

    intersection = words1 & words2
    union = words1 | words2

    similarity = len(intersection) / len(union)
    return similarity > threshold


async def get_cached_resume(
    user_id: int,
    job_title: str,
    vacancy_description: str,
    db_path: str,
) -> Optional[str]:
    """
    Look up a cached resume for user_id + job_title within the last 7 days.
    If found, increments the hits counter and returns the resume_text.
    Returns None if no valid cache entry exists.
    """
    title_hash = get_job_title_hash(job_title)
    cutoff = (datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS)).isoformat()

    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, resume_text
                FROM resume_cache
                WHERE user_id = ?
                  AND job_title_hash = ?
                  AND created_at > ?
                ORDER BY hits DESC, created_at DESC
                LIMIT 10
                """,
                (user_id, title_hash, cutoff),
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return None

        # Use the first (most-hit / most-recent) match — title hash already matched
        best_row = rows[0]
        entry_id = best_row["id"]
        resume_text = best_row["resume_text"]

        # Increment hit counter
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE resume_cache SET hits = hits + 1 WHERE id = ?",
                (entry_id,),
            )
            await db.commit()

        logger.info(
            "[resume_cache] Cache HIT user_id=%s job_title=%r entry_id=%s",
            user_id, job_title, entry_id,
        )
        return resume_text

    except Exception as exc:
        logger.exception("[resume_cache] get_cached_resume error: %s", exc)
        return None


async def cache_resume(
    user_id: int,
    job_title: str,
    vacancy_description: str,
    resume_text: str,
    db_path: str,
) -> None:
    """Insert a generated resume into the cache table."""
    title_hash = get_job_title_hash(job_title)
    vacancy_hash = get_vacancy_hash(vacancy_description)
    now = datetime.utcnow().isoformat()

    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT INTO resume_cache
                    (user_id, job_title_hash, vacancy_desc_hash, resume_text, created_at, hits)
                VALUES (?, ?, ?, ?, ?, 0)
                """,
                (user_id, title_hash, vacancy_hash, resume_text, now),
            )
            await db.commit()
        logger.info(
            "[resume_cache] Cached resume for user_id=%s job_title=%r",
            user_id, job_title,
        )
    except Exception as exc:
        logger.exception("[resume_cache] cache_resume error: %s", exc)


async def cleanup_expired_cache(db_path: str) -> int:
    """
    DELETE FROM resume_cache WHERE created_at < 7 days ago.
    Returns count of deleted rows.
    """
    cutoff = (datetime.utcnow() - timedelta(days=CACHE_TTL_DAYS)).isoformat()

    try:
        async with aiosqlite.connect(db_path) as db:
            cursor = await db.execute(
                "DELETE FROM resume_cache WHERE created_at < ?",
                (cutoff,),
            )
            deleted = cursor.rowcount
            await db.commit()
        logger.info("[resume_cache] Cleaned up %d expired cache entries", deleted)
        return deleted
    except Exception as exc:
        logger.exception("[resume_cache] cleanup_expired_cache error: %s", exc)
        return 0
