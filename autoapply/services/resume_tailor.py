"""
resume_tailor.py — Per-job resume tailoring service.

Given a candidate's base resume text and a job posting, this service uses GPT
to produce a tailored version that:
  • Rewrites the professional summary to echo the job's language
  • Reorders and expands the most-relevant skills/experience bullets
  • Injects ATS keywords from the job description
  • Stays under ~900 words so it fits a single-page resume

Results are cached in-memory keyed by (resume_hash, job_hash) to avoid
redundant API calls when the same candidate applies to similar postings.

Usage:
    from autoapply.services.resume_tailor import tailor_resume
    tailored = await tailor_resume(
        base_resume=user["resume_text"],
        job={"title": "...", "description": "...", "company": "..."},
    )
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# In-process LRU cache — maps (resume_hash, job_hash) → tailored_text
# Cleared on process restart; good enough for a long-running worker.
_CACHE: dict[tuple[str, str], str] = {}
_CACHE_MAX = 500  # evict oldest when full


def _hash(text: str) -> str:
    # usedforsecurity=False: SHA-1 here is a non-cryptographic cache key only
    return hashlib.sha1(text.encode("utf-8", errors="replace"), usedforsecurity=False).hexdigest()[:16]  # noqa: S324


def _cache_put(key: tuple[str, str], value: str) -> None:
    if len(_CACHE) >= _CACHE_MAX:
        # Evict 10% of entries (arbitrary order — dict insertion order in Py3.7+)
        for old_key in list(_CACHE.keys())[: _CACHE_MAX // 10]:
            del _CACHE[old_key]
    _CACHE[key] = value


async def _call_openai(prompt: str, system: str, max_tokens: int = 1200) -> str:
    """Call OpenAI / OpenRouter chat completions."""
    api_key = (
        os.getenv("OPENROUTER_API_KEY", "")
        or os.getenv("OPENAI_API_KEY", "")
    )
    if not api_key:
        raise ValueError("[resume_tailor] No API key configured")

    base_url = (
        "https://openrouter.ai/api/v1/chat/completions"
        if os.getenv("OPENROUTER_API_KEY")
        else "https://api.openai.com/v1/chat/completions"
    )
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    import aiohttp
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if "openrouter" in base_url:
        headers["HTTP-Referer"] = "https://resumeai-bot.ru"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.5,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            base_url,
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=45),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"[resume_tailor] API {resp.status}: {body[:200]}")
            data = await resp.json()
            return (
                data["choices"][0]["message"]["content"].strip()
            )


async def tailor_resume(
    base_resume: str,
    job: dict,
    language: str = "en",
) -> str:
    """
    Return a tailored version of base_resume for the given job.
    Falls back to base_resume on any error.

    Args:
        base_resume: The candidate's master resume text.
        job: Dict with keys 'title', 'description', 'company', 'location'.
        language: 'en' (default) or 'ru'.
    """
    if not base_resume or not base_resume.strip():
        return base_resume

    title = (job.get("title") or "").strip()
    description = (job.get("description") or "").strip()
    company = (job.get("company") or "").strip()

    if not description and not title:
        return base_resume  # nothing to tailor against

    # Cache lookup
    resume_key = _hash(base_resume)
    job_key = _hash(f"{title}{company}{description[:500]}")
    cache_key = (resume_key, job_key)
    if cache_key in _CACHE:
        logger.debug("[resume_tailor] cache hit for %s @ %s", title, company)
        return _CACHE[cache_key]

    lang_instruction = "Write entirely in English." if language != "ru" else "Write entirely in Russian."

    system = (
        "You are an expert resume writer and career coach. "
        "Your task is to tailor a candidate's resume for a specific job posting. "
        "Preserve all factual information — do NOT invent new experience or skills. "
        "Rewrite the summary, reorder bullets to lead with the most relevant ones, "
        "and naturally integrate keywords from the job description for ATS. "
        f"{lang_instruction} "
        "Output plain text only — no markdown headers (**, ##, etc.)."
    )

    prompt = f"""Tailor this resume for the job below.

=== JOB ===
Title: {title}
Company: {company}
Description (first 2000 chars):
{description[:2000]}

=== CANDIDATE'S CURRENT RESUME ===
{base_resume[:3000]}

=== INSTRUCTIONS ===
1. Rewrite the professional summary (3-4 sentences) so it speaks directly to this role.
2. Reorder experience bullets so the most relevant ones come first.
3. Expand or add skills that appear in the job description (only if genuinely held).
4. Keep total length under 900 words.
5. Plain text, section headers like "SUMMARY", "EXPERIENCE", "SKILLS", "EDUCATION".

Write the tailored resume now:"""

    try:
        tailored = await asyncio.wait_for(_call_openai(prompt, system), timeout=40)
        if len(tailored) < 100:
            logger.warning("[resume_tailor] suspiciously short result (%d chars)", len(tailored))
            return base_resume
        _cache_put(cache_key, tailored)
        logger.info("[resume_tailor] tailored resume for %r at %r (%d chars)", title, company, len(tailored))
        return tailored
    except Exception as exc:
        logger.warning("[resume_tailor] failed: %s — using base resume", exc)
        return base_resume


async def extract_ats_keywords(job: dict) -> list[str]:
    """
    Extract the top ~20 ATS keywords from a job description.
    Used by the bot's vacancy analysis handler for scoring purposes.
    Returns an empty list on failure.
    """
    description = (job.get("description") or job.get("title") or "").strip()
    if not description:
        return []

    system = (
        "You are an ATS expert. Extract the most important keywords from a job description. "
        "Return ONLY a JSON array of strings, e.g. [\"Python\", \"REST APIs\", \"agile\"]. "
        "No explanation."
    )
    prompt = f"Job description:\n{description[:2000]}\n\nReturn top 20 ATS keywords as JSON array:"

    try:
        response = await asyncio.wait_for(_call_openai(prompt, system, max_tokens=200), timeout=15)
        import json as _json
        # Strip markdown code fences if present
        clean = response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        keywords = _json.loads(clean)
        if isinstance(keywords, list):
            return [str(k) for k in keywords[:25]]
    except Exception as exc:
        logger.debug("[resume_tailor] extract_ats_keywords error: %s", exc)
    return []
