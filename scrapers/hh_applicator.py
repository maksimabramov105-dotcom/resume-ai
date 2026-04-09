"""
hh_applicator.py — Automated job application submission via hh.ru API
Requires user's OAuth access token (obtained via OAuth flow in the web app)
Docs: https://api.hh.ru/openapi/en/redoc#tag/Negotiations-(responses)
"""
import aiohttp
import asyncio
import logging
import json
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

HH_BASE = "https://api.hh.ru"
HH_APP_NAME = "ResumeAI-AutoApply/1.0 (resumeai.bot)"


def _make_headers(token: str) -> Dict:
    return {
        "User-Agent": HH_APP_NAME,
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }


async def get_user_resumes(token: str) -> List[Dict]:
    """
    GET /resumes/mine — fetch the authenticated user's resumes.
    Returns list of resume dicts, or empty list on error.
    """
    if not token:
        logger.warning("[hh_applicator] get_user_resumes called with empty token")
        return []

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{HH_BASE}/resumes/mine",
                headers=_make_headers(token),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    resumes = data.get("items", [])
                    logger.info(
                        f"[hh_applicator] get_user_resumes found {len(resumes)} resumes"
                    )
                    return resumes
                elif resp.status == 401:
                    logger.warning(
                        "[hh_applicator] get_user_resumes: token expired/invalid (401)"
                    )
                    return []
                elif resp.status == 403:
                    logger.warning("[hh_applicator] get_user_resumes: forbidden (403)")
                    return []
                else:
                    text = await resp.text()
                    logger.error(
                        f"[hh_applicator] get_user_resumes HTTP {resp.status}: {text[:200]}"
                    )
                    return []
    except asyncio.TimeoutError:
        logger.error("[hh_applicator] get_user_resumes timed out")
        return []
    except aiohttp.ClientError as e:
        logger.error(f"[hh_applicator] get_user_resumes network error: {e}")
        return []
    except Exception as e:
        logger.exception(f"[hh_applicator] get_user_resumes unexpected error: {e}")
        return []


async def upload_resume_text(
    token: str,
    resume_text: str,
    vacancy_id: str,
) -> Optional[str]:
    """
    Stub: hh.ru API does not support creating resumes from plain text.
    Instead, this function retrieves the user's first available resume_id
    from their existing hh.ru account resumes.

    Returns the resume_id string if found, or None if no resumes available.
    """
    logger.info(
        f"[hh_applicator] upload_resume_text: fetching existing resume for vacancy {vacancy_id}"
    )
    resumes = await get_user_resumes(token)
    if not resumes:
        logger.warning(
            "[hh_applicator] upload_resume_text: user has no resumes on hh.ru"
        )
        return None

    # Use the first available resume
    resume_id = resumes[0].get("id")
    if resume_id:
        logger.info(f"[hh_applicator] upload_resume_text: using resume_id={resume_id}")
        return str(resume_id)

    logger.warning("[hh_applicator] upload_resume_text: first resume has no id")
    return None


async def apply_to_vacancy(
    token: str,
    vacancy_id: str,
    resume_id: str,
    cover_letter: str = "",
) -> Dict:
    """
    POST /negotiations — submit a job application.
    Returns {"success": bool, "status_code": int, "error": str|None, "negotiation_id": str|None}

    Error codes handled:
      400 — already applied or validation error
      403 — token expired
      404 — vacancy closed/not found
      429 — rate limited
    """
    if not token:
        return {"success": False, "status_code": 0, "error": "token_missing", "negotiation_id": None}
    if not vacancy_id:
        return {"success": False, "status_code": 0, "error": "vacancy_id_missing", "negotiation_id": None}
    if not resume_id:
        return {"success": False, "status_code": 0, "error": "resume_id_missing", "negotiation_id": None}

    headers = _make_headers(token)
    # POST /negotiations uses form-encoded body
    headers["Content-Type"] = "application/x-www-form-urlencoded"

    payload = {
        "vacancy_id": vacancy_id,
        "resume_id": resume_id,
    }
    if cover_letter:
        payload["message"] = cover_letter

    logger.info(
        f"[hh_applicator] apply_to_vacancy: vacancy_id={vacancy_id} resume_id={resume_id}"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{HH_BASE}/negotiations",
                data=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                status_code = resp.status

                if status_code == 201:
                    # Successful application
                    try:
                        data = await resp.json()
                    except Exception:
                        data = {}
                    negotiation_id = str(data.get("id", ""))
                    logger.info(
                        f"[hh_applicator] Applied successfully: negotiation_id={negotiation_id}"
                    )
                    return {
                        "success": True,
                        "status_code": status_code,
                        "error": None,
                        "negotiation_id": negotiation_id,
                    }

                elif status_code == 400:
                    text = await resp.text()
                    # Check if it's an "already applied" error
                    error_msg = "already_applied" if "already" in text.lower() else "validation_error"
                    logger.warning(
                        f"[hh_applicator] apply_to_vacancy 400: {text[:300]}"
                    )
                    return {
                        "success": False,
                        "status_code": status_code,
                        "error": error_msg,
                        "negotiation_id": None,
                    }

                elif status_code == 403:
                    text = await resp.text()
                    logger.warning(
                        f"[hh_applicator] apply_to_vacancy 403 (token expired?): {text[:200]}"
                    )
                    return {
                        "success": False,
                        "status_code": status_code,
                        "error": "token_expired",
                        "negotiation_id": None,
                    }

                elif status_code == 404:
                    logger.warning(
                        f"[hh_applicator] apply_to_vacancy 404: vacancy {vacancy_id} closed/not found"
                    )
                    return {
                        "success": False,
                        "status_code": status_code,
                        "error": "vacancy_closed",
                        "negotiation_id": None,
                    }

                elif status_code == 429:
                    logger.warning("[hh_applicator] apply_to_vacancy 429: rate limited")
                    return {
                        "success": False,
                        "status_code": status_code,
                        "error": "rate_limited",
                        "negotiation_id": None,
                    }

                else:
                    text = await resp.text()
                    logger.error(
                        f"[hh_applicator] apply_to_vacancy HTTP {status_code}: {text[:300]}"
                    )
                    return {
                        "success": False,
                        "status_code": status_code,
                        "error": f"http_error_{status_code}",
                        "negotiation_id": None,
                    }

    except asyncio.TimeoutError:
        logger.error(
            f"[hh_applicator] apply_to_vacancy timed out for vacancy_id={vacancy_id}"
        )
        return {
            "success": False,
            "status_code": 0,
            "error": "timeout",
            "negotiation_id": None,
        }
    except aiohttp.ClientError as e:
        logger.error(f"[hh_applicator] apply_to_vacancy network error: {e}")
        return {
            "success": False,
            "status_code": 0,
            "error": f"network_error: {str(e)}",
            "negotiation_id": None,
        }
    except Exception as e:
        logger.exception(f"[hh_applicator] apply_to_vacancy unexpected error: {e}")
        return {
            "success": False,
            "status_code": 0,
            "error": f"unexpected_error: {str(e)}",
            "negotiation_id": None,
        }


async def check_application_status(token: str, negotiation_id: str) -> str:
    """
    GET /negotiations/{id} — check status of a submitted application.
    Returns status string: "response", "viewed", "interview", "discard", etc.
    Returns "unknown" on error.
    """
    if not token or not negotiation_id:
        logger.warning("[hh_applicator] check_application_status: missing token or negotiation_id")
        return "unknown"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{HH_BASE}/negotiations/{negotiation_id}",
                headers=_make_headers(token),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("state", {}).get("id", "unknown")
                    logger.debug(
                        f"[hh_applicator] check_application_status "
                        f"negotiation_id={negotiation_id} status={status}"
                    )
                    return status
                elif resp.status == 401:
                    logger.warning("[hh_applicator] check_application_status: token expired (401)")
                    return "token_expired"
                elif resp.status == 404:
                    logger.warning(
                        f"[hh_applicator] check_application_status: "
                        f"negotiation {negotiation_id} not found (404)"
                    )
                    return "not_found"
                else:
                    text = await resp.text()
                    logger.error(
                        f"[hh_applicator] check_application_status HTTP "
                        f"{resp.status}: {text[:200]}"
                    )
                    return "unknown"
    except asyncio.TimeoutError:
        logger.error("[hh_applicator] check_application_status timed out")
        return "unknown"
    except aiohttp.ClientError as e:
        logger.error(f"[hh_applicator] check_application_status network error: {e}")
        return "unknown"
    except Exception as e:
        logger.exception(f"[hh_applicator] check_application_status unexpected error: {e}")
        return "unknown"


async def get_application_stats(token: str) -> Dict:
    """
    GET /negotiations?status=all — fetch all negotiations and return counts by status.
    Returns {"total": int, "by_status": {"response": int, "viewed": int, ...}, "error": str|None}
    """
    if not token:
        logger.warning("[hh_applicator] get_application_stats called with empty token")
        return {"total": 0, "by_status": {}, "error": "token_missing"}

    all_negotiations = []
    page = 0
    per_page = 100

    try:
        async with aiohttp.ClientSession() as session:
            while True:
                params = {
                    "status": "all",
                    "page": page,
                    "per_page": per_page,
                }
                async with session.get(
                    f"{HH_BASE}/negotiations",
                    params=params,
                    headers=_make_headers(token),
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("items", [])
                        all_negotiations.extend(items)
                        total_pages = data.get("pages", 1)
                        logger.debug(
                            f"[hh_applicator] get_application_stats page={page}/{total_pages}"
                        )
                        if page >= total_pages - 1:
                            break
                        page += 1
                        await asyncio.sleep(1.0)
                    elif resp.status == 401:
                        logger.warning(
                            "[hh_applicator] get_application_stats: token expired (401)"
                        )
                        return {"total": 0, "by_status": {}, "error": "token_expired"}
                    else:
                        text = await resp.text()
                        logger.error(
                            f"[hh_applicator] get_application_stats HTTP "
                            f"{resp.status}: {text[:200]}"
                        )
                        return {"total": 0, "by_status": {}, "error": f"http_error_{resp.status}"}

    except asyncio.TimeoutError:
        logger.error("[hh_applicator] get_application_stats timed out")
        return {"total": 0, "by_status": {}, "error": "timeout"}
    except aiohttp.ClientError as e:
        logger.error(f"[hh_applicator] get_application_stats network error: {e}")
        return {"total": 0, "by_status": {}, "error": f"network_error: {str(e)}"}
    except Exception as e:
        logger.exception(f"[hh_applicator] get_application_stats unexpected error: {e}")
        return {"total": 0, "by_status": {}, "error": f"unexpected_error: {str(e)}"}

    # Tally counts by status
    by_status: Dict[str, int] = {}
    for neg in all_negotiations:
        state = neg.get("state", {}).get("id", "unknown")
        by_status[state] = by_status.get(state, 0) + 1

    logger.info(
        f"[hh_applicator] get_application_stats total={len(all_negotiations)} by_status={by_status}"
    )
    return {
        "total": len(all_negotiations),
        "by_status": by_status,
        "error": None,
    }
