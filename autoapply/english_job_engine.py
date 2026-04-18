"""
english_job_engine.py — English job board search aggregator.

Sources:
  Adzuna     — US/UK/CA/AU jobs (free API key from developer.adzuna.com)
  The Muse   — US tech/startup jobs (open, no key needed)
  Arbeitnow  — Remote English jobs (open)
  RemoteOK   — Remote dev jobs (open JSON feed)

Each source returns normalized dicts:
  id, title, company, location, salary, url, apply_url,
  description, source, apply_email, tags
"""
import asyncio
import logging
import os
import re
from typing import Optional

import httpx

from autoapply.config import (
    ADZUNA_APP_ID,
    ADZUNA_APP_KEY,
    ENGLISH_JOB_SOURCES,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "ResumeAI-AutoApply/1.0 (support@resumeai-bot.ru)"}


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()[:2000]


def _normalize(data: dict) -> dict:
    return {
        "id": str(data.get("id", "")),
        "title": data.get("title", ""),
        "company": data.get("company", ""),
        "location": data.get("location", "Remote"),
        "salary": data.get("salary", ""),
        "url": data.get("url", ""),
        "apply_url": data.get("apply_url") or data.get("url", ""),
        "description": _clean_html(data.get("description", "")),
        "source": data.get("source", "unknown"),
        "apply_email": data.get("apply_email"),
        "tags": data.get("tags", []),
    }


# ── Adzuna ─────────────────────────────────────────────────────────────────────

async def search_adzuna(
    query: str,
    location: str = "",
    country: str = "us",
    limit: int = 50,
) -> list:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        logger.debug("[adzuna] skipped — ADZUNA_APP_ID or ADZUNA_APP_KEY not set")
        return []
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": query,
        "results_per_page": min(limit, 50),
        "content-type": "application/json",
    }
    if location:
        params["where"] = location
    try:
        async with httpx.AsyncClient(timeout=12, headers=_HEADERS) as client:
            r = await client.get(
                f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
                params=params,
            )
            if r.status_code != 200:
                logger.warning("[adzuna] HTTP %s: %s", r.status_code, r.text[:200])
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("[adzuna] request failed: %s", exc)
        return []

    jobs = []
    for item in data.get("results", []):
        loc = item.get("location", {}).get("display_name", location or "US")
        sal_min = item.get("salary_min")
        sal_max = item.get("salary_max")
        sal = f"${int(sal_min):,}–${int(sal_max):,}/yr" if sal_min and sal_max else ""
        jobs.append(_normalize({
            "id": f"adzuna_{item.get('id', '')}",
            "title": item.get("title", ""),
            "company": item.get("company", {}).get("display_name", ""),
            "location": loc,
            "salary": sal,
            "url": item.get("redirect_url", ""),
            "apply_url": item.get("redirect_url", ""),
            "description": _clean_html(item.get("description", "")),
            "source": "adzuna",
        }))
    logger.info("[adzuna] found %d jobs for %r in %s", len(jobs), query, country)
    return jobs


# ── The Muse ───────────────────────────────────────────────────────────────────

async def search_themuse(query: str, location: str = "", limit: int = 20) -> list:
    params: dict = {"page": 0}
    if query:
        params["category"] = query
    if location:
        params["location"] = location
    try:
        async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
            r = await client.get("https://www.themuse.com/api/public/jobs", params=params)
            if r.status_code != 200:
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("[themuse] request failed: %s", exc)
        return []

    jobs = []
    for item in data.get("results", [])[:limit]:
        locs = ", ".join(l.get("name", "") for l in item.get("locations", []))
        jobs.append(_normalize({
            "id": f"themuse_{item.get('id', '')}",
            "title": item.get("name", ""),
            "company": item.get("company", {}).get("name", ""),
            "location": locs or "US",
            "salary": "",
            "url": item.get("refs", {}).get("landing_page", ""),
            "apply_url": item.get("refs", {}).get("landing_page", ""),
            "description": _clean_html(item.get("contents", "")),
            "source": "themuse",
        }))
    logger.info("[themuse] found %d jobs for %r", len(jobs), query)
    return jobs


# ── Arbeitnow ──────────────────────────────────────────────────────────────────

async def search_arbeitnow(query: str, limit: int = 30) -> list:
    params = {"search": query} if query else {}
    try:
        async with httpx.AsyncClient(timeout=10, headers=_HEADERS) as client:
            r = await client.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params=params,
            )
            if r.status_code != 200:
                return []
            data = r.json()
    except Exception as exc:
        logger.warning("[arbeitnow] request failed: %s", exc)
        return []

    jobs = []
    for item in data.get("data", [])[:limit]:
        jobs.append(_normalize({
            "id": f"arbeitnow_{item.get('slug', '')}",
            "title": item.get("title", ""),
            "company": item.get("company_name", ""),
            "location": item.get("location", "") or ("Remote" if item.get("remote") else "Europe"),
            "salary": "",
            "url": item.get("url", ""),
            "apply_url": item.get("url", ""),
            "description": _clean_html(item.get("description", "")),
            "source": "arbeitnow",
            "tags": item.get("tags", []),
        }))
    logger.info("[arbeitnow] found %d jobs for %r", len(jobs), query)
    return jobs


# ── RemoteOK ───────────────────────────────────────────────────────────────────

async def search_remoteok(query: str, limit: int = 30) -> list:
    tag = query.lower().replace(" ", "-") if query else "dev"
    try:
        async with httpx.AsyncClient(
            timeout=10,
            headers={**_HEADERS, "Accept": "application/json"},
        ) as client:
            r = await client.get(f"https://remoteok.com/api?tag={tag}")
            if r.status_code != 200:
                return []
            items = r.json()
    except Exception as exc:
        logger.warning("[remoteok] request failed: %s", exc)
        return []

    # First item is a legal notice object — skip it
    if items and isinstance(items[0], dict) and "legal" in items[0]:
        items = items[1:]

    jobs = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        sal_min = item.get("salary_min")
        sal_max = item.get("salary_max")
        sal = f"${int(sal_min):,}–${int(sal_max):,}/yr" if sal_min and sal_max else ""
        jobs.append(_normalize({
            "id": f"remoteok_{item.get('id', '')}",
            "title": item.get("position", ""),
            "company": item.get("company", ""),
            "location": item.get("location", "") or "Remote",
            "salary": sal,
            "url": item.get("url", ""),
            "apply_url": item.get("apply_url", "") or item.get("url", ""),
            "description": _clean_html(item.get("description", "")),
            "source": "remoteok",
            "tags": item.get("tags", []),
        }))
    logger.info("[remoteok] found %d jobs for %r", len(jobs), query)
    return jobs


# ── Aggregator ─────────────────────────────────────────────────────────────────

async def search_english_jobs(
    query: str,
    location: str = "",
    country: str = "us",
    sources: Optional[list] = None,
    limit_per_source: int = 30,
) -> list:
    """
    Search all configured English job sources in parallel.
    Returns deduplicated, normalized list sorted by source diversity.
    """
    if sources is None:
        sources = ENGLISH_JOB_SOURCES

    tasks = []
    if "adzuna" in sources:
        tasks.append(search_adzuna(query, location, country, limit_per_source))
    if "themuse" in sources:
        tasks.append(search_themuse(query, location, limit_per_source))
    if "arbeitnow" in sources:
        tasks.append(search_arbeitnow(query, limit_per_source))
    if "remoteok" in sources:
        tasks.append(search_remoteok(query, limit_per_source))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs: list = []
    for r in results:
        if isinstance(r, list):
            all_jobs.extend(r)
        else:
            logger.warning("[english_jobs] source error: %s", r)

    # Deduplicate by URL
    seen: set = set()
    deduped = []
    for j in all_jobs:
        url = j.get("url", "") or j.get("id", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(j)

    logger.info("[english_jobs] %d unique jobs for %r from %s", len(deduped), query, sources)
    return deduped


# ── AI Cover Letter ────────────────────────────────────────────────────────────

async def generate_cover_letter(
    resume_text: str,
    job: dict,
    openrouter_key: str = "",
) -> str:
    """Generate an AI cover letter tailored to a specific English job posting."""
    api_key = openrouter_key or os.getenv("OPENROUTER_API_KEY", "") or OPENAI_API_KEY
    if not api_key:
        return ""

    base_url = (
        "https://openrouter.ai/api/v1"
        if os.getenv("OPENROUTER_API_KEY")
        else "https://api.openai.com/v1"
    )

    prompt = (
        f"Write a professional, concise cover letter (3 short paragraphs, max 180 words).\n\n"
        f"Job: {job.get('title', '')} at {job.get('company', '')}\n"
        f"Location: {job.get('location', '')}\n"
        f"Description: {job.get('description', '')[:600]}\n\n"
        f"Candidate resume (excerpt):\n{resume_text[:800]}\n\n"
        f"Rules: professional English, no clichés, end with call to action, "
        f"sign as [Your Name]. Return only the letter text."
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 350,
                    "temperature": 0.7,
                },
            )
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("[cover_letter] generation failed: %s", exc)
        return ""
