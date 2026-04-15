"""
worker.py — AutoApply background job processor.

Runs independently:
    python -m autoapply.worker

Or as a systemd service. Processes active campaigns every WORKER_INTERVAL seconds.
"""
import asyncio
import logging
import os
import random
import signal
import sys
from datetime import datetime, date
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from autoapply.config import (
    AUTOAPPLY_DB,
    LOGS_DIR,
    MAX_APPLY_DELAY,
    MIN_APPLY_DELAY,
    PLANS,
    WEBAPP_BASE_URL,
    WORKER_INTERVAL,
    BOT_TOKEN,
)
from autoapply.autoapply_db import (
    get_active_campaigns,
    get_user_by_id,
    is_vacancy_applied,
    log_application,
    reset_daily_counts,
    update_campaign_last_run,
    get_cached_vacancies,
    cache_vacancy,
)
from autoapply.payments import send_telegram_message

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOGS_DIR, "worker.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("autoapply_worker")

# ── Shutdown flag ─────────────────────────────────────────────────────────────
_shutdown = False
_last_reset_date: Optional[date] = None


def _handle_sigterm(signum, frame):
    global _shutdown
    logger.info("[worker] SIGTERM received — shutting down gracefully")
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)


# ── Scraper adapter ───────────────────────────────────────────────────────────

async def _fetch_vacancies(
    platform: str, job_title: str, location: str, salary_min: int, experience: str
) -> list:
    """
    Attempt to import the platform-specific scraper and fetch vacancies.
    Falls back to cache if scraper is unavailable.
    Returns list of vacancy dicts.
    """
    # Check cache first (fresh within 1 hour)
    cached = await get_cached_vacancies(platform, job_title, location, max_age_hours=1, db_path=AUTOAPPLY_DB)
    if cached:
        logger.info(
            "[worker] cache hit: %d vacancies for platform=%s title=%s",
            len(cached), platform, job_title,
        )
        return cached

    vacancies = []
    try:
        if platform == "hh":
            scrapers_path = os.path.join(ROOT, "scrapers")
            if scrapers_path not in sys.path:
                sys.path.insert(0, scrapers_path)
            from hh_scraper import search_vacancies  # type: ignore
            vacancies = await search_vacancies(
                job_title=job_title,
                location=location,
                salary_min=salary_min,
                experience=experience,
            )
        elif platform == "superjob":
            scrapers_path = os.path.join(ROOT, "scrapers")
            if scrapers_path not in sys.path:
                sys.path.insert(0, scrapers_path)
            from superjob_scraper import search_vacancies as sj_search  # type: ignore
            vacancies = await sj_search(
                job_title=job_title,
                location=location,
                salary_min=salary_min,
            )
        else:
            logger.warning("[worker] unknown platform=%s, skipping", platform)
            return []

        # Filter out any non-dict items returned by the scraper (e.g. error strings)
        vacancies = [v for v in vacancies if isinstance(v, dict)]

        # Cache fetched vacancies
        for v in vacancies:
            await cache_vacancy(
                platform=platform,
                vacancy_id=str(v.get("id", "")),
                title=v.get("title", ""),
                company=v.get("company", ""),
                location=v.get("location", ""),
                salary=str(v.get("salary", "")),
                description=v.get("description", ""),
                url=v.get("url", ""),
                db_path=AUTOAPPLY_DB,
            )

    except ImportError as exc:
        logger.warning("[worker] scraper for platform=%s not available: %s", platform, exc)
    except Exception as exc:
        logger.exception("[worker] fetch_vacancies error platform=%s: %s", platform, exc)

    return vacancies


async def _generate_resume(user: dict, vacancy: dict) -> str:
    """
    Attempt to use the resume_generator module for a tailored resume.
    Falls back to raw resume_text if unavailable.
    """
    base_resume = user.get("resume_text") or ""
    if not base_resume:
        return ""

    try:
        gen_path = os.path.join(ROOT, "bot")
        if gen_path not in sys.path:
            sys.path.insert(0, gen_path)
        from resume_generator import generate_tailored_resume  # type: ignore
        tailored = await generate_tailored_resume(
            resume_text=base_resume,
            vacancy_title=vacancy.get("title", ""),
            vacancy_description=vacancy.get("description", ""),
        )
        return tailored
    except ImportError:
        logger.debug("[worker] resume_generator not available, using base resume")
        return base_resume
    except Exception as exc:
        logger.warning("[worker] resume_generator error: %s — using base resume", exc)
        return base_resume


async def _try_apply_hh(user: dict, vacancy: dict, resume_text: str) -> bool:
    """
    Attempt to submit an application via hh_applicator.
    Returns True on success.
    """
    hh_token = user.get("hh_token")
    hh_resume_id = user.get("hh_resume_id")
    if not hh_token or not hh_resume_id:
        return False

    try:
        applicator_path = os.path.join(ROOT, "scrapers")
        if applicator_path not in sys.path:
            sys.path.insert(0, applicator_path)
        from hh_applicator import apply_to_vacancy  # type: ignore
        success = await apply_to_vacancy(
            vacancy_id=str(vacancy.get("id", "")),
            resume_id=hh_resume_id,
            access_token=hh_token,
            cover_letter=resume_text[:500] if resume_text else "",
        )
        return bool(success)
    except ImportError:
        logger.debug("[worker] hh_applicator not available")
        return False
    except Exception as exc:
        logger.warning("[worker] hh_applicator error: %s", exc)
        return False


# ── Campaign processor ────────────────────────────────────────────────────────

async def process_campaign(campaign: dict) -> int:
    """
    Process a single campaign. Returns number of applications sent.
    Never raises — all errors are caught and logged.
    """
    campaign_id = campaign["id"]
    user_id = campaign["user_id"]
    job_title = campaign["job_title"]
    location = campaign.get("location", "")
    salary_min = campaign.get("salary_min", 0)
    experience = campaign.get("experience", "")
    platforms = campaign.get("platforms", ["hh"])
    campaign_daily_limit = campaign.get("daily_limit", 10)

    logger.info(
        "[worker] processing campaign_id=%s user_id=%s title=%s platforms=%s",
        campaign_id, user_id, job_title, platforms,
    )

    user = await get_user_by_id(user_id, AUTOAPPLY_DB)
    if not user:
        logger.error("[worker] user_id=%s not found, skipping campaign", user_id)
        return 0

    # How many more applications can this user send today?
    user_daily_limit = user.get("daily_limit", 3)
    apps_today = user.get("applications_today", 0)
    remaining_user = max(0, user_daily_limit - apps_today)
    remaining = min(remaining_user, campaign_daily_limit)

    if remaining <= 0:
        logger.info(
            "[worker] campaign_id=%s user_id=%s: daily limit reached (%d/%d)",
            campaign_id, user_id, apps_today, user_daily_limit,
        )
        return 0

    sent_count = 0

    for platform in platforms:
        if sent_count >= remaining or _shutdown:
            break

        vacancies = await _fetch_vacancies(platform, job_title, location, salary_min, experience)
        logger.info(
            "[worker] campaign_id=%s platform=%s fetched %d vacancies",
            campaign_id, platform, len(vacancies),
        )

        for vacancy in vacancies:
            if sent_count >= remaining or _shutdown:
                break

            if not isinstance(vacancy, dict):
                logger.warning("[worker] skipping non-dict vacancy item: %r", type(vacancy))
                continue

            vacancy_id = str(vacancy.get("id") or vacancy.get("vacancy_id", ""))
            if not vacancy_id:
                continue

            # Skip already applied
            already = await is_vacancy_applied(vacancy_id, user_id, AUTOAPPLY_DB)
            if already:
                continue

            vacancy_title = vacancy.get("title", "Вакансия")
            company_name = vacancy.get("company", "")
            vacancy_url = vacancy.get("url", "")

            # Generate (possibly tailored) resume
            resume_text = await _generate_resume(user, vacancy)

            # Try actual API application for hh
            applied_via_api = False
            if platform == "hh":
                applied_via_api = await _try_apply_hh(user, vacancy, resume_text)

            apply_status = "sent" if applied_via_api else "queued"

            try:
                await log_application(
                    campaign_id=campaign_id,
                    user_id=user_id,
                    platform=platform,
                    vacancy_id=vacancy_id,
                    vacancy_title=vacancy_title,
                    company_name=company_name,
                    vacancy_url=vacancy_url,
                    resume_used=resume_text[:500] if resume_text else "",
                    db_path=AUTOAPPLY_DB,
                )
                sent_count += 1
                logger.info(
                    "[worker] logged application: campaign=%s vacancy_id=%s company=%s status=%s",
                    campaign_id, vacancy_id, company_name, apply_status,
                )
            except Exception as exc:
                logger.exception("[worker] log_application error: %s", exc)
                continue

            # Human-like delay between applications
            if sent_count < remaining:
                delay = random.randint(MIN_APPLY_DELAY, MAX_APPLY_DELAY)
                logger.debug("[worker] sleeping %ds before next application", delay)
                await asyncio.sleep(delay)

    await update_campaign_last_run(campaign_id, AUTOAPPLY_DB)
    return sent_count


# ── Telegram summary ──────────────────────────────────────────────────────────

async def notify_user(user_id: int, sent_today: int) -> None:
    """Send a Telegram summary to the user if their account is linked."""
    user = await get_user_by_id(user_id, AUTOAPPLY_DB)
    if not user:
        return
    telegram_id = user.get("telegram_id")
    if not telegram_id:
        return

    apps_today = user.get("applications_today", 0)
    apps_total = user.get("applications_total", 0)
    responses = user.get("responses_received", 0)

    text = (
        f"АвтоОтклик: отправлено ещё {sent_today} заявок\n"
        f"Сегодня: {apps_today} | Всего: {apps_total} | Ответов: {responses}\n"
        f"{WEBAPP_BASE_URL}/app"
    )
    await send_telegram_message(telegram_id, text)


# ── Main loop ─────────────────────────────────────────────────────────────────

async def run_once() -> None:
    """Single worker pass: process all active campaigns."""
    global _last_reset_date

    today = date.today()
    if _last_reset_date != today:
        logger.info("[worker] new day detected — resetting daily counts")
        await reset_daily_counts(AUTOAPPLY_DB)
        _last_reset_date = today

    campaigns = await get_active_campaigns(AUTOAPPLY_DB)
    logger.info("[worker] found %d active campaigns", len(campaigns))

    # Group sent counts by user for summary notifications
    user_sent: dict[int, int] = {}

    for campaign in campaigns:
        if _shutdown:
            break
        try:
            sent = await process_campaign(campaign)
            if sent > 0:
                uid = campaign["user_id"]
                user_sent[uid] = user_sent.get(uid, 0) + sent
        except Exception as exc:
            logger.exception(
                "[worker] unhandled error in campaign_id=%s: %s",
                campaign.get("id"), exc,
            )
            # Never crash the whole loop — continue with next campaign

    # Send per-user Telegram summaries
    for uid, count in user_sent.items():
        try:
            await notify_user(uid, count)
        except Exception as exc:
            logger.exception("[worker] notify_user error uid=%s: %s", uid, exc)


async def main() -> None:
    """Main entry point. Loops forever with WORKER_INTERVAL sleep."""
    logger.info("[worker] AutoApply worker started. Interval=%ds", WORKER_INTERVAL)

    # Ensure DB tables exist
    from autoapply.autoapply_db import init_db
    await init_db(AUTOAPPLY_DB)

    while not _shutdown:
        start = asyncio.get_event_loop().time()
        try:
            await run_once()
        except Exception as exc:
            logger.exception("[worker] run_once top-level error: %s", exc)

        if _shutdown:
            break

        elapsed = asyncio.get_event_loop().time() - start
        sleep_for = max(0.0, WORKER_INTERVAL - elapsed)
        logger.info("[worker] cycle done in %.1fs, sleeping %.0fs", elapsed, sleep_for)

        # Sleep in small chunks so we can react to shutdown quickly
        slept = 0.0
        while slept < sleep_for and not _shutdown:
            chunk = min(5.0, sleep_for - slept)
            await asyncio.sleep(chunk)
            slept += chunk

    logger.info("[worker] shutdown complete")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())
