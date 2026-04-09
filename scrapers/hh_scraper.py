"""
hh_scraper.py — hh.ru vacancy scraper using official API
Docs: https://api.hh.ru/openapi/en/redoc
Rate limit: 1 request/second for anonymous, respect it
"""
import aiohttp
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# City → hh.ru area_id mapping
AREA_IDS = {
    "москва": 1, "москве": 1, "moscow": 1,
    "санкт-петербург": 2, "питер": 2, "спб": 2, "saint-petersburg": 2,
    "екатеринбург": 3, "новосибирск": 4, "казань": 88,
    "нижний новгород": 66, "омск": 68, "самара": 78,
    "уфа": 99, "ростов-на-дону": 76, "красноярск": 62,
    "воронеж": 26, "пермь": 72, "волгоград": 24,
    "удалённо": 1, "remote": 1, "россия": 113,
}

HH_BASE = "https://api.hh.ru"
HH_APP_NAME = "ResumeAI-AutoApply/1.0 (resumeai.bot)"

EXPERIENCE_MAP = {
    "нет опыта": "noExperience",
    "1-3 года": "between1And3",
    "3-6 лет": "between3And6",
    "более 6 лет": "moreThan6",
}


async def get_area_id(location: str) -> int:
    """Lookup area_id by location string. Falls back to 113 (Russia) if not found."""
    if not location:
        return 113
    normalized = location.strip().lower()
    area_id = AREA_IDS.get(normalized, None)
    if area_id is None:
        logger.warning(f"[hh_scraper] Unknown location '{location}', defaulting to Russia (113)")
        return 113
    return area_id


async def search_vacancies(
    job_title: str,
    location: str,
    salary_min: int = 0,
    experience: str = "",
    page: int = 0,
    per_page: int = 100,
) -> Dict:
    """
    GET /vacancies — single page search.
    Returns raw API response dict, or empty dict on error.
    """
    area_id = await get_area_id(location)
    experience_code = EXPERIENCE_MAP.get(experience, "")

    params = {
        "text": job_title,
        "area": area_id,
        "page": page,
        "per_page": min(per_page, 100),
        "currency": "RUR",
        "only_with_salary": "false",
    }
    if salary_min and salary_min > 0:
        params["salary"] = salary_min
    if experience_code:
        params["experience"] = experience_code

    headers = {
        "User-Agent": HH_APP_NAME,
        "Accept": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{HH_BASE}/vacancies",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.debug(
                        f"[hh_scraper] search_vacancies page={page} found={data.get('found', 0)}"
                    )
                    return data
                elif resp.status == 429:
                    logger.warning("[hh_scraper] Rate limited (429). Backing off 5 seconds.")
                    await asyncio.sleep(5)
                    return {}
                else:
                    text = await resp.text()
                    logger.error(
                        f"[hh_scraper] search_vacancies HTTP {resp.status}: {text[:200]}"
                    )
                    return {}
    except asyncio.TimeoutError:
        logger.error("[hh_scraper] search_vacancies timed out")
        return {}
    except aiohttp.ClientError as e:
        logger.error(f"[hh_scraper] search_vacancies network error: {e}")
        return {}
    except Exception as e:
        logger.exception(f"[hh_scraper] search_vacancies unexpected error: {e}")
        return {}


def _normalize_vacancy(item: Dict) -> Dict:
    """Convert raw hh.ru vacancy item to normalized dict."""
    salary = item.get("salary") or {}
    salary_from = salary.get("from")
    salary_to = salary.get("to")
    currency = salary.get("currency", "RUR")

    if salary_from and salary_to:
        salary_str = f"{salary_from}–{salary_to} {currency}"
    elif salary_from:
        salary_str = f"от {salary_from} {currency}"
    elif salary_to:
        salary_str = f"до {salary_to} {currency}"
    else:
        salary_str = "не указана"

    employer = item.get("employer") or {}
    address = item.get("address") or {}
    area = item.get("area") or {}

    location_str = (
        address.get("city")
        or area.get("name")
        or ""
    )

    snippet = item.get("snippet") or {}
    description_short = snippet.get("requirement") or snippet.get("responsibility") or ""
    # Strip HTML tags from snippet
    import re
    description_short = re.sub(r"<[^>]+>", "", description_short).strip()

    return {
        "platform": "hh",
        "vacancy_id": str(item.get("id", "")),
        "title": item.get("name", ""),
        "company": employer.get("name", ""),
        "location": location_str,
        "salary": salary_str,
        "description_short": description_short[:500],
        "url": item.get("alternate_url", ""),
        "employer_id": str(employer.get("id", "")),
    }


async def scrape_vacancies(
    job_title: str,
    location: str,
    salary_min: int = 0,
    experience: str = "",
    max_vacancies: int = 500,
) -> List[Dict]:
    """
    Paginate through hh.ru results and return normalized vacancy list.
    Respects rate limit: 1 request/second.
    """
    all_vacancies: List[Dict] = []
    page = 0
    per_page = 100

    logger.info(
        f"[hh_scraper] Starting scrape: title='{job_title}' location='{location}' "
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
        )

        items = data.get("items", [])
        if not items:
            logger.info(f"[hh_scraper] No more items on page {page}, stopping.")
            break

        for item in items:
            if len(all_vacancies) >= max_vacancies:
                break
            try:
                normalized = _normalize_vacancy(item)
                all_vacancies.append(normalized)
            except Exception as e:
                logger.warning(f"[hh_scraper] Failed to normalize vacancy {item.get('id')}: {e}")

        total_pages = data.get("pages", 1)
        logger.info(
            f"[hh_scraper] Page {page}/{total_pages}, collected {len(all_vacancies)} vacancies so far"
        )

        if page >= total_pages - 1:
            break

        page += 1
        await asyncio.sleep(1.0)  # Respect rate limit: 1 req/sec for anonymous

    logger.info(f"[hh_scraper] Scrape complete. Total: {len(all_vacancies)} vacancies.")
    return all_vacancies


async def get_vacancy_description(vacancy_id: str) -> str:
    """
    GET /vacancies/{id} — fetch full vacancy description text.
    Returns plain text (HTML stripped), or empty string on error.
    """
    headers = {
        "User-Agent": HH_APP_NAME,
        "Accept": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{HH_BASE}/vacancies/{vacancy_id}",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    raw_desc = data.get("description", "")
                    # Strip HTML tags
                    import re
                    clean = re.sub(r"<[^>]+>", " ", raw_desc)
                    clean = re.sub(r"\s+", " ", clean).strip()
                    logger.debug(
                        f"[hh_scraper] get_vacancy_description id={vacancy_id} len={len(clean)}"
                    )
                    return clean
                elif resp.status == 404:
                    logger.warning(f"[hh_scraper] Vacancy {vacancy_id} not found (404)")
                    return ""
                elif resp.status == 429:
                    logger.warning("[hh_scraper] Rate limited on get_vacancy_description")
                    await asyncio.sleep(5)
                    return ""
                else:
                    text = await resp.text()
                    logger.error(
                        f"[hh_scraper] get_vacancy_description HTTP {resp.status}: {text[:200]}"
                    )
                    return ""
    except asyncio.TimeoutError:
        logger.error(f"[hh_scraper] get_vacancy_description timed out for id={vacancy_id}")
        return ""
    except aiohttp.ClientError as e:
        logger.error(f"[hh_scraper] get_vacancy_description network error: {e}")
        return ""
    except Exception as e:
        logger.exception(f"[hh_scraper] get_vacancy_description unexpected error: {e}")
        return ""


async def get_user_resumes(hh_token: str) -> List[Dict]:
    """
    GET /resumes/mine — fetch the authenticated user's resumes.
    Requires a valid OAuth Bearer token.
    Returns list of resume dicts, or empty list on error.
    """
    if not hh_token:
        logger.warning("[hh_scraper] get_user_resumes called with empty token")
        return []

    headers = {
        "User-Agent": HH_APP_NAME,
        "Accept": "application/json",
        "Authorization": f"Bearer {hh_token}",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{HH_BASE}/resumes/mine",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    resumes = data.get("items", [])
                    logger.info(f"[hh_scraper] get_user_resumes found {len(resumes)} resumes")
                    return resumes
                elif resp.status == 401:
                    logger.warning("[hh_scraper] get_user_resumes: token expired/invalid (401)")
                    return []
                elif resp.status == 403:
                    logger.warning("[hh_scraper] get_user_resumes: forbidden (403)")
                    return []
                else:
                    text = await resp.text()
                    logger.error(
                        f"[hh_scraper] get_user_resumes HTTP {resp.status}: {text[:200]}"
                    )
                    return []
    except asyncio.TimeoutError:
        logger.error("[hh_scraper] get_user_resumes timed out")
        return []
    except aiohttp.ClientError as e:
        logger.error(f"[hh_scraper] get_user_resumes network error: {e}")
        return []
    except Exception as e:
        logger.exception(f"[hh_scraper] get_user_resumes unexpected error: {e}")
        return []
