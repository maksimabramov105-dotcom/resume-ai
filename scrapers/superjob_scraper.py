"""
superjob_scraper.py — SuperJob.ru vacancy scraper
API docs: https://api.superjob.ru/
Requires free API key from superjob.ru/api/doc
"""
import aiohttp
import asyncio
import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

SJ_BASE = "https://api.superjob.ru/2.0"

EXPERIENCE_MAP = {
    "нет опыта": 1,        # no experience
    "1-3 года": 2,          # 1–3 years
    "3-6 лет": 3,           # 3–6 years
    "более 6 лет": 4,       # more than 6 years
}


def _normalize_vacancy(item: Dict) -> Dict:
    """Convert raw SuperJob vacancy item to normalized dict."""
    salary_from = item.get("payment_from") or 0
    salary_to = item.get("payment_to") or 0
    currency = item.get("currency", "rub").upper()

    if salary_from and salary_to:
        salary_str = f"{salary_from}–{salary_to} {currency}"
    elif salary_from:
        salary_str = f"от {salary_from} {currency}"
    elif salary_to:
        salary_str = f"до {salary_to} {currency}"
    else:
        salary_str = "не указана"

    client = item.get("client") or {}
    town = item.get("town") or {}
    work = item.get("work") or {}

    location_str = town.get("title", "")

    raw_description = item.get("candidat") or item.get("vacancyRichText") or ""
    clean_description = re.sub(r"<[^>]+>", " ", raw_description)
    clean_description = re.sub(r"\s+", " ", clean_description).strip()

    return {
        "platform": "superjob",
        "vacancy_id": str(item.get("id", "")),
        "title": item.get("profession", ""),
        "company": client.get("title", ""),
        "location": location_str,
        "salary": salary_str,
        "description_short": clean_description[:500],
        "url": item.get("link", ""),
        "employer_id": str(client.get("id", "")),
    }


async def search_vacancies(
    job_title: str,
    location: str,
    salary_min: int = 0,
    experience: str = "",
    page: int = 0,
    per_page: int = 100,
    api_key: str = "",
) -> Dict:
    """
    GET /vacancies/ — single page search on SuperJob.
    Returns raw API response dict, or empty dict on error.
    If api_key is empty, logs a warning and returns empty dict.
    """
    if not api_key:
        logger.warning(
            "[superjob_scraper] search_vacancies called without api_key — skipping SuperJob"
        )
        return {}

    experience_id = EXPERIENCE_MAP.get(experience, 0)

    params = {
        "keyword": job_title,
        "count": min(per_page, 100),
        "page": page,
    }
    if location:
        params["town"] = location
    if salary_min and salary_min > 0:
        params["payment_from"] = salary_min
    if experience_id:
        params["experience"] = experience_id

    headers = {
        "X-Api-App-Id": api_key,
        "Accept": "application/json",
        "User-Agent": "ResumeAI-AutoApply/1.0",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SJ_BASE}/vacancies/",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.debug(
                        f"[superjob_scraper] search_vacancies page={page} "
                        f"total={data.get('total', 0)}"
                    )
                    return data
                elif resp.status == 429:
                    logger.warning("[superjob_scraper] Rate limited (429). Backing off 3 seconds.")
                    await asyncio.sleep(3)
                    return {}
                elif resp.status == 401:
                    logger.error(
                        "[superjob_scraper] Unauthorized (401) — invalid or expired API key"
                    )
                    return {}
                elif resp.status == 403:
                    logger.error(
                        "[superjob_scraper] Forbidden (403) — API key lacks permissions"
                    )
                    return {}
                else:
                    text = await resp.text()
                    logger.error(
                        f"[superjob_scraper] search_vacancies HTTP {resp.status}: {text[:200]}"
                    )
                    return {}
    except asyncio.TimeoutError:
        logger.error("[superjob_scraper] search_vacancies timed out")
        return {}
    except aiohttp.ClientError as e:
        logger.error(f"[superjob_scraper] search_vacancies network error: {e}")
        return {}
    except Exception as e:
        logger.exception(f"[superjob_scraper] search_vacancies unexpected error: {e}")
        return {}


async def scrape_vacancies(
    job_title: str,
    location: str,
    salary_min: int = 0,
    experience: str = "",
    max_vacancies: int = 300,
    api_key: str = "",
) -> List[Dict]:
    """
    Paginate through SuperJob results and return normalized vacancy list.
    Returns empty list (with warning) if api_key is not provided.
    Rate limit: 0.5 seconds between requests.
    """
    if not api_key:
        logger.warning(
            "[superjob_scraper] scrape_vacancies called without api_key — returning empty list"
        )
        return []

    all_vacancies: List[Dict] = []
    page = 0
    per_page = 100

    logger.info(
        f"[superjob_scraper] Starting scrape: title='{job_title}' location='{location}' "
        f"salary_min={salary_min} experience='{experience}' max={max_vacancies}"
    )

    while len(all_vacancies) < max_vacancies:
        data = await search_vacancies(
            job_title=job_title,
            location=location,
            salary_min=salary_min,
            experience=experience,
            page=page,
            per_page=per_page,
            api_key=api_key,
        )

        if not data:
            logger.info(f"[superjob_scraper] Empty response on page {page}, stopping.")
            break

        objects = data.get("objects", [])
        if not objects:
            logger.info(f"[superjob_scraper] No items on page {page}, stopping.")
            break

        for item in objects:
            if len(all_vacancies) >= max_vacancies:
                break
            try:
                normalized = _normalize_vacancy(item)
                all_vacancies.append(normalized)
            except Exception as e:
                logger.warning(
                    f"[superjob_scraper] Failed to normalize vacancy {item.get('id')}: {e}"
                )

        total = data.get("total", 0)
        total_pages = (total + per_page - 1) // per_page if total else 1
        logger.info(
            f"[superjob_scraper] Page {page}/{total_pages}, "
            f"collected {len(all_vacancies)} vacancies so far"
        )

        more = data.get("more", False)
        if not more:
            break

        page += 1
        await asyncio.sleep(0.5)  # Respect rate limit

    logger.info(
        f"[superjob_scraper] Scrape complete. Total: {len(all_vacancies)} vacancies."
    )
    return all_vacancies


async def get_vacancy_description(vacancy_id: str, api_key: str) -> str:
    """
    GET /vacancies/{id} — fetch full description for a SuperJob vacancy.
    Returns plain text, or empty string on error.
    """
    if not api_key:
        logger.warning("[superjob_scraper] get_vacancy_description called without api_key")
        return ""

    headers = {
        "X-Api-App-Id": api_key,
        "Accept": "application/json",
        "User-Agent": "ResumeAI-AutoApply/1.0",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{SJ_BASE}/vacancies/{vacancy_id}/",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    raw = data.get("vacancyRichText") or data.get("candidat") or ""
                    clean = re.sub(r"<[^>]+>", " ", raw)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    logger.debug(
                        f"[superjob_scraper] get_vacancy_description id={vacancy_id} "
                        f"len={len(clean)}"
                    )
                    return clean
                elif resp.status == 404:
                    logger.warning(
                        f"[superjob_scraper] Vacancy {vacancy_id} not found (404)"
                    )
                    return ""
                elif resp.status == 429:
                    logger.warning("[superjob_scraper] Rate limited on get_vacancy_description")
                    await asyncio.sleep(3)
                    return ""
                else:
                    text = await resp.text()
                    logger.error(
                        f"[superjob_scraper] get_vacancy_description HTTP "
                        f"{resp.status}: {text[:200]}"
                    )
                    return ""
    except asyncio.TimeoutError:
        logger.error(
            f"[superjob_scraper] get_vacancy_description timed out for id={vacancy_id}"
        )
        return ""
    except aiohttp.ClientError as e:
        logger.error(f"[superjob_scraper] get_vacancy_description network error: {e}")
        return ""
    except Exception as e:
        logger.exception(
            f"[superjob_scraper] get_vacancy_description unexpected error: {e}"
        )
        return ""
