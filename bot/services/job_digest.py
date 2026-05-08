"""
job_digest.py — Daily personalised job-match digest for Telegram bot users.

Flow:
  1. For each user who has a specialty (profile), fetch jobs from international boards.
  2. Score each job against the user's profile with a fast keyword+GPT ranker.
  3. Pick the top 3–5 and send a Telegram push.
  4. Rate-limit: at most one digest per user per 20 hours (digest_sent_at column).

Called by the APScheduler job registered in run.py at 09:00 UTC daily.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# How many jobs to fetch from each source
_FETCH_PER_SOURCE = 20
# How many top jobs to show in the digest
_TOP_N = 5
# Minimum hours between digests per user
_COOLDOWN_HOURS = 20


# ── Scoring ───────────────────────────────────────────────────────────────────

def _keyword_score(job: dict, keywords: list[str]) -> float:
    """Fast keyword overlap score (0-1) — no API call."""
    text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("company", ""),
        job.get("location", ""),
    ]).lower()
    if not text or not keywords:
        return 0.0
    matched = sum(1 for kw in keywords if kw.lower() in text)
    return matched / max(len(keywords), 1)


def _extract_keywords(specialty: Optional[str], skills: Optional[str]) -> list[str]:
    """Extract search keywords from user profile fields."""
    raw = f"{specialty or ''} {skills or ''}"
    # Split on comma/semicolon/newline and strip
    tokens = [
        t.strip().lower()
        for part in raw.replace(",", " ").replace(";", " ").replace("\n", " ").split()
        for t in [part.strip()]
        if len(t.strip()) > 2
    ]
    # Deduplicate preserving order
    seen: set[str] = set()
    result = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result[:30]  # cap at 30 keywords


async def _ai_rerank(
    jobs: list[dict],
    specialty: Optional[str],
    skills: Optional[str],
    max_jobs: int = _TOP_N,
) -> list[dict]:
    """
    Use GPT to pick the top max_jobs most relevant jobs.
    Falls back to keyword order if the AI call fails.
    Input jobs are already sorted by keyword score.
    """
    if not jobs:
        return []

    # Only send the top 15 candidates to the AI (cost control)
    candidates = jobs[:15]

    try:
        from services.openai_service import chat_completion

        profile_str = ""
        if specialty:
            profile_str += f"Specialty: {specialty}\n"
        if skills:
            profile_str += f"Skills: {skills[:300]}\n"

        job_list = "\n".join(
            f"{i+1}. [{j.get('title','?')}] at {j.get('company','?')} — {j.get('location','?')}"
            for i, j in enumerate(candidates)
        )

        prompt = (
            f"You are a career coach. A candidate has this profile:\n{profile_str}\n"
            f"Here are {len(candidates)} job postings (numbered):\n{job_list}\n\n"
            f"Return ONLY a comma-separated list of the {max_jobs} most relevant job numbers "
            "in order of relevance (best first). Example: 3,1,7,2,5\n"
            "No explanation, just the numbers."
        )

        response, _ = await chat_completion(
            [{"role": "user", "content": prompt}],
            max_tokens=40,
        )

        # Parse "3,1,7,2,5"
        indices = []
        for part in response.strip().split(","):
            try:
                idx = int(part.strip()) - 1  # 1-based → 0-based
                if 0 <= idx < len(candidates):
                    indices.append(idx)
            except ValueError:
                continue

        if indices:
            return [candidates[i] for i in indices[:max_jobs]]

    except Exception as exc:
        logger.warning("[job_digest] AI rerank error: %s", exc)

    # Fallback: keyword-sorted top N
    return candidates[:max_jobs]


# ── Message formatting ────────────────────────────────────────────────────────

def _format_digest(jobs: list[dict], specialty: Optional[str], lang: str) -> str:
    """Format the digest as Telegram HTML."""
    if lang == "ru":
        header = (
            f"📬 <b>Подборка вакансий на сегодня</b>\n"
            f"{('для ' + specialty) if specialty else ''}\n\n"
        )
        footer = "\n\n<i>Нажмите на название, чтобы открыть вакансию. Настройки: /digest</i>"
    else:
        header = (
            f"📬 <b>Today's job matches</b>\n"
            f"{('for ' + specialty) if specialty else ''}\n\n"
        )
        footer = "\n\n<i>Tap a title to open the job. Settings: /digest</i>"

    lines = []
    for i, job in enumerate(jobs, 1):
        title = job.get("title", "Job opening")
        company = job.get("company", "")
        location = job.get("location", "")
        url = job.get("url") or job.get("apply_url", "")
        meta = " · ".join(filter(None, [company, location]))
        if url:
            line = f"{i}. <a href=\"{url}\">{title}</a>"
        else:
            line = f"{i}. <b>{title}</b>"
        if meta:
            line += f"\n   <i>{meta}</i>"
        lines.append(line)

    return header + "\n\n".join(lines) + footer


# ── Main send loop ────────────────────────────────────────────────────────────

async def send_daily_digest(bot) -> None:
    """
    Send daily job digest to all users who have a specialty set.
    Respects the _COOLDOWN_HOURS rate limit per user.
    """
    # Import here to avoid circular deps at module level
    try:
        from database.db import get_all_users
    except ImportError:
        logger.error("[job_digest] Could not import get_all_users")
        return

    # The autoapply english_job_engine may live at a different path on the VPS
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)

    try:
        from autoapply.english_job_engine import search_english_jobs
    except ImportError:
        logger.error("[job_digest] Could not import search_english_jobs — autoapply not in path")
        return

    users = await get_all_users()
    now = datetime.now(timezone.utc)
    sent = 0
    skipped = 0

    for user in users:
        specialty = getattr(user, "specialty", None)
        if not specialty:
            skipped += 1
            continue  # no profile — nothing to match against

        # Rate-limit: skip if already sent within cooldown window
        digest_sent_at = getattr(user, "digest_sent_at", None)
        if digest_sent_at:
            if isinstance(digest_sent_at, str):
                try:
                    digest_sent_at = datetime.fromisoformat(digest_sent_at).replace(tzinfo=timezone.utc)
                except ValueError:
                    digest_sent_at = None
            if digest_sent_at and (now - digest_sent_at) < timedelta(hours=_COOLDOWN_HOURS):
                skipped += 1
                continue

        # Check opt-out
        if not getattr(user, "digest_enabled", True):
            skipped += 1
            continue

        try:
            skills_text = getattr(user, "skills_text", None) or ""
            keywords = _extract_keywords(specialty, skills_text)
            query = specialty[:80]  # truncate long specialties for API query

            jobs = await search_english_jobs(
                query=query,
                limit_per_source=_FETCH_PER_SOURCE,
            )

            if not jobs:
                logger.debug("[job_digest] no jobs found for %s", user.telegram_id)
                continue

            # Keyword-score and sort
            for job in jobs:
                job["_score"] = _keyword_score(job, keywords)
            jobs.sort(key=lambda j: j["_score"], reverse=True)

            # AI rerank top candidates
            top_jobs = await _ai_rerank(jobs, specialty, skills_text)

            if not top_jobs:
                continue

            lang = getattr(user, "language", None) or "en"
            text = _format_digest(top_jobs, specialty, lang)

            await bot.send_message(
                user.telegram_id,
                text,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

            # Update digest_sent_at in DB
            try:
                from database.db import update_user_digest_sent_at
                await update_user_digest_sent_at(user.telegram_id)
            except Exception:
                pass  # non-fatal

            sent += 1
            await asyncio.sleep(0.05)  # 50ms between sends — Telegram flood guard

        except Exception as exc:
            logger.warning("[job_digest] failed for user %s: %s", user.telegram_id, exc)

    logger.info("[job_digest] daily digest done: sent=%d skipped=%d", sent, skipped)


# ── Opt-out handler helper (called from bot/handlers/digest_settings.py) ──────

async def toggle_digest(telegram_id: int, enabled: bool) -> None:
    """Enable or disable daily digest for a user."""
    try:
        from database.db import update_user_digest_enabled
        await update_user_digest_enabled(telegram_id, enabled)
    except Exception as exc:
        logger.error("[job_digest] toggle_digest error: %s", exc)
