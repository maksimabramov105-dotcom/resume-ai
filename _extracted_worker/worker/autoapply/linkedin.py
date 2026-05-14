"""
linkedin.py — LinkedIn Easy Apply automation via Playwright.

IMPORTANT RATE LIMITS:
- Max 30 applications per session
- 2-3 minute delays between applications
- Never run more than 1 session per LinkedIn account simultaneously
- Detect CAPTCHAs and pause campaign if detected

Ported from: scrapers/linkedin_applicator.py
Changes vs source:
  - Replaced logging with structlog
  - Replaced Russian strings/comments with English
  - Wrapped as a class (LinkedInApplicator) for use by the FastAPI worker route
  - _fill_form_defaults: removed Russian placeholder keywords
"""
import asyncio
import random
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

try:
    from playwright.async_api import async_playwright
    from playwright.async_api import TimeoutError as PWTimeout

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("linkedin.playwright_not_installed", detail="LinkedIn automation disabled")

LINKEDIN_BASE = "https://www.linkedin.com"
LOGIN_URL = f"{LINKEDIN_BASE}/login"
JOBS_SEARCH_URL = f"{LINKEDIN_BASE}/jobs/search/"

MAX_APPS_PER_SESSION = 30


class CaptchaDetectedError(Exception):
    """Raised when LinkedIn presents a CAPTCHA or security checkpoint."""


def _not_available_result(func_name: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": "playwright_not_installed",
        "function": func_name,
    }


async def _login(page: Any, email: str, password: str) -> None:
    """
    Perform LinkedIn login. Raises CaptchaDetectedError if a challenge is
    detected after submitting credentials.
    """
    logger.info("linkedin.login.navigating")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(random.uniform(1.5, 2.5))

    await page.fill('input[name="session_key"]', email)
    await asyncio.sleep(random.uniform(0.3, 0.7))
    await page.fill('input[name="session_password"]', password)
    await asyncio.sleep(random.uniform(0.3, 0.7))
    await page.click('button[type="submit"]')

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except PWTimeout:
        logger.warning("linkedin.login.page_load_timeout")

    await asyncio.sleep(random.uniform(2.0, 3.0))
    await _check_captcha(page)

    current_url = page.url
    if "login" in current_url or "checkpoint" in current_url:
        raise CaptchaDetectedError(
            f"Login failed or security checkpoint encountered: {current_url}"
        )

    logger.info("linkedin.login.success")


async def _check_captcha(page: Any) -> None:
    """Check for CAPTCHA or security challenge. Raises CaptchaDetectedError if found."""
    challenge_selectors = [
        'iframe[src*="challenge"]',
        'iframe[src*="captcha"]',
        'iframe[src*="recaptcha"]',
        '#captcha-internal',
        '.captcha-container',
        '[data-testid="challenge"]',
        'h1:has-text("Let\'s do a quick security check")',
        'h1:has-text("Security Verification")',
    ]
    for selector in challenge_selectors:
        try:
            element = await page.wait_for_selector(selector, timeout=1500)
            if element:
                raise CaptchaDetectedError(
                    f"CAPTCHA/security challenge detected: selector={selector}"
                )
        except CaptchaDetectedError:
            raise
        except PWTimeout:
            pass
        except Exception as exc:
            logger.debug("linkedin.captcha_check_minor_error", error=str(exc))


async def _is_easy_apply(page: Any) -> bool:
    """Return True if the current job posting has an Easy Apply button."""
    try:
        btn = await page.wait_for_selector(
            'button.jobs-apply-button:has-text("Easy Apply")',
            timeout=3000,
        )
        return btn is not None
    except (PWTimeout, Exception):
        return False


async def _fill_contact_info(page: Any, user_profile: dict[str, Any]) -> None:
    """Fill in contact info fields if present on the current form step."""
    parts = user_profile.get("name", "").strip().split()
    first = parts[0] if parts else ""
    last = " ".join(parts[1:]) if len(parts) > 1 else ""

    field_map = {
        'input[id*="phoneNumber"], input[aria-label*="Phone"]': user_profile.get("phone", ""),
        'input[id*="firstName"], input[aria-label*="First name"]': first,
        'input[id*="lastName"], input[aria-label*="Last name"]': last,
        'input[id*="email"], input[aria-label*="Email"]': user_profile.get("email", ""),
    }
    for selector, value in field_map.items():
        if not value:
            continue
        try:
            field = await page.query_selector(selector)
            if field:
                current_val = await field.input_value()
                if not current_val:
                    await field.fill(value)
                    await asyncio.sleep(random.uniform(0.2, 0.5))
        except Exception as exc:
            logger.debug("linkedin.fill_contact_error", selector=selector, error=str(exc))


async def _upload_resume(page: Any, resume_pdf_path: str) -> None:
    """Upload resume PDF to file input if present."""
    if not resume_pdf_path:
        return
    import os

    if not os.path.exists(resume_pdf_path):
        logger.warning("linkedin.resume_not_found", path=resume_pdf_path)
        return
    try:
        file_input = await page.query_selector('input[type="file"]')
        if file_input:
            await file_input.set_input_files(resume_pdf_path)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            logger.debug("linkedin.resume_uploaded", path=resume_pdf_path)
    except Exception as exc:
        logger.warning("linkedin.resume_upload_error", error=str(exc))


async def _fill_form_defaults(page: Any, user_profile: dict[str, Any]) -> None:
    """Fill text questions and select elements with sensible defaults."""
    experience_years = str(user_profile.get("experience_years", "1"))

    # Fill empty text inputs using experience years for numeric-looking fields
    try:
        text_inputs = await page.query_selector_all(
            'input[type="text"]:not([aria-label*="ame"]):not([aria-label*="hone"])'
            ':not([aria-label*="mail"])'
        )
        for inp in text_inputs:
            try:
                val = await inp.input_value()
                if not val:
                    placeholder = await inp.get_attribute("placeholder") or ""
                    if any(kw in placeholder.lower() for kw in ["year", "experience"]):
                        await inp.fill(experience_years)
                    else:
                        await inp.fill(experience_years)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            except Exception:
                pass
    except Exception as exc:
        logger.debug("linkedin.fill_defaults_text_error", error=str(exc))

    # Handle select elements — pick first non-empty option
    try:
        selects = await page.query_selector_all("select")
        for sel in selects:
            try:
                current = await sel.input_value()
                if not current or current == "Select an option":
                    options = await sel.query_selector_all("option")
                    for opt in options:
                        val = await opt.get_attribute("value") or ""
                        if val and val not in ("", "Select an option"):
                            await sel.select_option(value=val)
                            break
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            except Exception:
                pass
    except Exception as exc:
        logger.debug("linkedin.fill_defaults_select_error", error=str(exc))


class LinkedInApplicator:
    """
    High-level wrapper for LinkedIn Easy Apply automation.

    Usage:
        applicator = LinkedInApplicator()
        result = await applicator.apply(email, password, job_title, location)
    """

    async def apply(
        self,
        email: str,
        password: str,
        job_title: str,
        location: str,
        user_profile: dict[str, Any] | None = None,
        resume_pdf_path: str = "",
        max_applications: int = MAX_APPS_PER_SESSION,
    ) -> dict[str, Any]:
        """
        Search LinkedIn for Easy Apply jobs then run an application session.
        Returns a summary dict with applied_count and per-job results.
        """
        if not PLAYWRIGHT_AVAILABLE:
            return _not_available_result("LinkedInApplicator.apply")

        profile = user_profile or {}

        # Step 1: find jobs
        jobs = await _search_jobs(email, password, job_title, location, max_applications)

        if not jobs:
            return {
                "success": True,
                "applied_count": 0,
                "results": [],
                "detail": "No Easy Apply jobs found for the given criteria",
            }

        # Step 2: apply to each job
        results = await _run_application_session(
            email=email,
            password=password,
            jobs=jobs,
            user_profile=profile,
            resume_pdf_path=resume_pdf_path,
        )

        applied_count = sum(1 for r in results if r.get("success"))
        return {
            "success": True,
            "applied_count": applied_count,
            "results": results,
        }


async def _search_jobs(
    email: str,
    password: str,
    job_title: str,
    location: str,
    max_jobs: int = 30,
) -> list[dict[str, Any]]:
    """
    Search LinkedIn for Easy Apply jobs.
    Returns a list of job dicts: {title, company, location, job_id, url, has_easy_apply}
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("linkedin.search_jobs.playwright_unavailable")
        return []

    jobs: list[dict[str, Any]] = []

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()
            try:
                await _login(page, email, password)

                search_params = (
                    f"?keywords={job_title.replace(' ', '%20')}"
                    f"&location={location.replace(' ', '%20')}"
                    f"&f_LF=f_AL"  # Easy Apply filter
                    f"&sortBy=DD"  # Most recent
                )
                search_url = JOBS_SEARCH_URL + search_params
                logger.info("linkedin.search_jobs.navigating", url=search_url)
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(random.uniform(2.0, 3.5))
                await _check_captcha(page)

                # Scroll to load more job cards
                for _ in range(3):
                    await page.keyboard.press("End")
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                job_cards = await page.query_selector_all(
                    ".job-card-container, .jobs-search-results__list-item"
                )
                logger.info("linkedin.search_jobs.cards_found", count=len(job_cards))

                for card in job_cards:
                    if len(jobs) >= max_jobs:
                        break
                    try:
                        title_el = await card.query_selector(
                            ".job-card-list__title, .job-card-container__link"
                        )
                        company_el = await card.query_selector(
                            ".job-card-container__company-name, "
                            ".job-card-container__primary-description"
                        )
                        location_el = await card.query_selector(
                            ".job-card-container__metadata-item"
                        )
                        link_el = await card.query_selector('a[href*="/jobs/view/"]')

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        loc = (await location_el.inner_text()).strip() if location_el else ""
                        href = await link_el.get_attribute("href") or "" if link_el else ""

                        job_id = ""
                        if "/jobs/view/" in href:
                            parts = href.split("/jobs/view/")
                            if len(parts) > 1:
                                job_id = parts[1].split("/")[0].split("?")[0]

                        full_url = (
                            f"{LINKEDIN_BASE}/jobs/view/{job_id}/" if job_id else href
                        )

                        easy_apply_badge = await card.query_selector(
                            '[aria-label*="Easy Apply"], .job-card-container__apply-method'
                        )
                        has_easy_apply = easy_apply_badge is not None

                        if title and has_easy_apply:
                            jobs.append(
                                {
                                    "title": title,
                                    "company": company,
                                    "location": loc,
                                    "job_id": job_id,
                                    "url": full_url,
                                    "has_easy_apply": has_easy_apply,
                                }
                            )
                    except Exception as exc:
                        logger.warning("linkedin.search_jobs.card_parse_error", error=str(exc))

                logger.info("linkedin.search_jobs.complete", easy_apply_count=len(jobs))

            except CaptchaDetectedError:
                raise
            except Exception as exc:
                logger.exception("linkedin.search_jobs.inner_error", error=str(exc))
            finally:
                await browser.close()

    except CaptchaDetectedError:
        raise
    except Exception as exc:
        logger.exception("linkedin.search_jobs.outer_error", error=str(exc))

    return jobs


async def _apply_to_job(
    email: str,
    password: str,
    job_url: str,
    user_profile: dict[str, Any],
    resume_pdf_path: str,
) -> dict[str, Any]:
    """
    Apply to a single LinkedIn job using Easy Apply.
    Returns {"success": bool, "error": str|None, "job_url": str}
    """
    if not PLAYWRIGHT_AVAILABLE:
        return _not_available_result("_apply_to_job")

    logger.info("linkedin.apply_to_job.started", job_url=job_url)

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = await context.new_page()
            try:
                await _login(page, email, password)

                await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(random.uniform(2.0, 3.0))
                await _check_captcha(page)

                if not await _is_easy_apply(page):
                    logger.warning("linkedin.apply_to_job.no_easy_apply_button", url=job_url)
                    return {
                        "success": False,
                        "error": "no_easy_apply_button",
                        "job_url": job_url,
                    }

                await page.click('button.jobs-apply-button:has-text("Easy Apply")')
                await asyncio.sleep(random.uniform(1.5, 2.5))

                max_steps = 10
                for step in range(1, max_steps + 1):
                    logger.debug("linkedin.apply_to_job.step", step=step, url=job_url)

                    await _fill_contact_info(page, user_profile)
                    await _upload_resume(page, resume_pdf_path)
                    await _fill_form_defaults(page, user_profile)
                    await asyncio.sleep(random.uniform(0.8, 1.5))

                    # Check for Submit button
                    submit_btn = None
                    try:
                        submit_btn = await page.wait_for_selector(
                            'button[aria-label="Submit application"], '
                            'button:has-text("Submit application")',
                            timeout=2000,
                        )
                    except PWTimeout:
                        pass

                    if submit_btn:
                        await submit_btn.click()
                        await asyncio.sleep(random.uniform(2.0, 3.0))
                        logger.info("linkedin.apply_to_job.submitted", url=job_url)
                        return {"success": True, "error": None, "job_url": job_url}

                    # Check for Next / Continue / Review
                    next_btn = None
                    for selector in [
                        'button[aria-label="Continue to next step"]',
                        'button[aria-label="Review your application"]',
                        'button:has-text("Next")',
                        'button:has-text("Continue")',
                        'button:has-text("Review")',
                    ]:
                        try:
                            next_btn = await page.wait_for_selector(selector, timeout=1500)
                            if next_btn:
                                break
                        except PWTimeout:
                            pass

                    if next_btn:
                        await next_btn.click()
                        await asyncio.sleep(random.uniform(1.0, 2.0))
                    else:
                        # No recognizable button — check if modal was dismissed
                        try:
                            await page.wait_for_selector(".artdeco-modal", timeout=1500)
                        except PWTimeout:
                            logger.info(
                                "linkedin.apply_to_job.modal_closed_assuming_success",
                                url=job_url,
                            )
                            return {"success": True, "error": None, "job_url": job_url}
                        break

                logger.warning("linkedin.apply_to_job.max_steps_reached", url=job_url)
                return {"success": False, "error": "max_steps_reached", "job_url": job_url}

            except CaptchaDetectedError as exc:
                logger.warning("linkedin.apply_to_job.captcha", error=str(exc))
                return {
                    "success": False,
                    "error": f"captcha_detected: {exc}",
                    "job_url": job_url,
                }
            except PWTimeout as exc:
                logger.error("linkedin.apply_to_job.playwright_timeout", error=str(exc))
                return {
                    "success": False,
                    "error": f"playwright_timeout: {exc}",
                    "job_url": job_url,
                }
            except Exception as exc:
                logger.exception("linkedin.apply_to_job.inner_error", error=str(exc))
                return {
                    "success": False,
                    "error": f"unexpected_error: {exc}",
                    "job_url": job_url,
                }
            finally:
                await browser.close()

    except Exception as exc:
        logger.exception("linkedin.apply_to_job.outer_error", error=str(exc))
        return {"success": False, "error": f"browser_error: {exc}", "job_url": job_url}


async def _run_application_session(
    email: str,
    password: str,
    jobs: list[dict[str, Any]],
    user_profile: dict[str, Any],
    resume_pdf_path: str,
) -> list[dict[str, Any]]:
    """
    Run a full application session for a list of jobs.
    Respects MAX_APPS_PER_SESSION and 2-3 minute delays between applications.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return [_not_available_result("_run_application_session")]

    results: list[dict[str, Any]] = []
    applied_count = 0

    for idx, job in enumerate(jobs):
        if applied_count >= MAX_APPS_PER_SESSION:
            logger.info("linkedin.session.limit_reached", limit=MAX_APPS_PER_SESSION)
            break

        job_url = job.get("url", "")
        if not job_url:
            logger.warning("linkedin.session.job_no_url")
            continue

        result = await _apply_to_job(
            email=email,
            password=password,
            job_url=job_url,
            user_profile=user_profile,
            resume_pdf_path=resume_pdf_path,
        )
        result["job_title"] = job.get("title", "")
        result["company"] = job.get("company", "")
        results.append(result)

        if result["success"]:
            applied_count += 1
            logger.info(
                "linkedin.session.applied",
                count=f"{applied_count}/{MAX_APPS_PER_SESSION}",
                title=job.get("title"),
                company=job.get("company"),
            )
        else:
            error = result.get("error", "")
            if "captcha_detected" in error:
                logger.warning("linkedin.session.captcha_pausing")
                break

        # 2-3 minute delay between applications
        if applied_count < MAX_APPS_PER_SESSION and idx < len(jobs) - 1:
            delay = random.uniform(120, 180)
            logger.info("linkedin.session.delay_between_applications", delay_s=round(delay))
            await asyncio.sleep(delay)

    logger.info(
        "linkedin.session.complete",
        applied_count=applied_count,
        total_results=len(results),
    )
    return results
