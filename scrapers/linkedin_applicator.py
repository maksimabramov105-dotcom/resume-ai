"""
linkedin_applicator.py — LinkedIn Easy Apply automation via Playwright
Uses async Playwright for headless Chrome automation.

IMPORTANT RATE LIMITS:
- Max 30 applications per session
- 2-3 minute delays between applications
- Never run more than 1 session per LinkedIn account simultaneously
- Detect CAPTCHAs and pause campaign if detected
"""
import asyncio
import logging
import random
import json
from typing import List, Dict, Optional
from datetime import datetime

try:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not installed. LinkedIn automation disabled.")

logger = logging.getLogger(__name__)

LINKEDIN_BASE = "https://www.linkedin.com"
LOGIN_URL = f"{LINKEDIN_BASE}/login"
JOBS_SEARCH_URL = f"{LINKEDIN_BASE}/jobs/search/"

MAX_APPS_PER_SESSION = 30


class CaptchaDetectedError(Exception):
    """Raised when LinkedIn presents a CAPTCHA challenge."""
    pass


def _not_available_result(func_name: str) -> Dict:
    return {
        "success": False,
        "error": "playwright_not_installed",
        "function": func_name,
    }


async def _login(page, email: str, password: str) -> None:
    """
    Perform LinkedIn login. Raises CaptchaDetectedError if a challenge is detected.
    """
    logger.info("[linkedin_applicator] Navigating to login page")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
    await asyncio.sleep(random.uniform(1.5, 2.5))

    # Fill credentials
    await page.fill('input[name="session_key"]', email)
    await asyncio.sleep(random.uniform(0.3, 0.7))
    await page.fill('input[name="session_password"]', password)
    await asyncio.sleep(random.uniform(0.3, 0.7))
    await page.click('button[type="submit"]')

    # Wait for navigation
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
    except PWTimeout:
        logger.warning("[linkedin_applicator] Login page load timed out, checking state")

    await asyncio.sleep(random.uniform(2.0, 3.0))

    # Check for CAPTCHA
    await _check_captcha(page)

    current_url = page.url
    if "login" in current_url or "checkpoint" in current_url:
        raise CaptchaDetectedError(
            f"Login failed or security checkpoint encountered: {current_url}"
        )

    logger.info("[linkedin_applicator] Login successful")


async def _check_captcha(page) -> None:
    """Check for CAPTCHA or security challenge. Raises CaptchaDetectedError if found."""
    try:
        # Common CAPTCHA/challenge selectors
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
            except PWTimeout:
                pass
    except CaptchaDetectedError:
        raise
    except Exception as e:
        logger.debug(f"[linkedin_applicator] _check_captcha check error (non-critical): {e}")


async def is_easy_apply(page) -> bool:
    """Return True if the current job posting has an Easy Apply button."""
    try:
        btn = await page.wait_for_selector(
            'button.jobs-apply-button:has-text("Easy Apply")',
            timeout=3000,
        )
        return btn is not None
    except PWTimeout:
        return False
    except Exception:
        return False


async def search_jobs(
    email: str,
    password: str,
    job_title: str,
    location: str,
    max_jobs: int = 30,
) -> List[Dict]:
    """
    Search LinkedIn for jobs using the given criteria.
    Returns a list of job dicts (only Easy Apply jobs included).

    Each job dict: {title, company, location, job_id, url, has_easy_apply}
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("[linkedin_applicator] search_jobs: Playwright not installed")
        return []

    jobs: List[Dict] = []

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
                # Login
                await _login(page, email, password)

                # Navigate to job search with Easy Apply filter
                search_params = (
                    f"?keywords={job_title.replace(' ', '%20')}"
                    f"&location={location.replace(' ', '%20')}"
                    f"&f_LF=f_AL"  # Easy Apply filter
                    f"&sortBy=DD"  # Most recent
                )
                search_url = JOBS_SEARCH_URL + search_params
                logger.info(f"[linkedin_applicator] Navigating to jobs search: {search_url}")
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(random.uniform(2.0, 3.5))

                await _check_captcha(page)

                # Scroll to load job cards
                for _ in range(3):
                    await page.keyboard.press("End")
                    await asyncio.sleep(random.uniform(1.0, 2.0))

                # Scrape job cards
                job_cards = await page.query_selector_all(
                    '.job-card-container, .jobs-search-results__list-item'
                )
                logger.info(
                    f"[linkedin_applicator] Found {len(job_cards)} job cards"
                )

                for card in job_cards:
                    if len(jobs) >= max_jobs:
                        break
                    try:
                        title_el = await card.query_selector(
                            '.job-card-list__title, .job-card-container__link'
                        )
                        company_el = await card.query_selector(
                            '.job-card-container__company-name, '
                            '.job-card-container__primary-description'
                        )
                        location_el = await card.query_selector(
                            '.job-card-container__metadata-item'
                        )
                        link_el = await card.query_selector('a[href*="/jobs/view/"]')

                        title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        loc = (await location_el.inner_text()).strip() if location_el else ""

                        href = ""
                        if link_el:
                            href = await link_el.get_attribute("href") or ""

                        # Extract job_id from URL
                        job_id = ""
                        if "/jobs/view/" in href:
                            parts = href.split("/jobs/view/")
                            if len(parts) > 1:
                                job_id = parts[1].split("/")[0].split("?")[0]

                        full_url = (
                            f"{LINKEDIN_BASE}/jobs/view/{job_id}/"
                            if job_id
                            else href
                        )

                        # Check Easy Apply badge on card
                        easy_apply_badge = await card.query_selector(
                            '[aria-label*="Easy Apply"], .job-card-container__apply-method'
                        )
                        has_easy_apply = easy_apply_badge is not None

                        if title and has_easy_apply:
                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": loc,
                                "job_id": job_id,
                                "url": full_url,
                                "has_easy_apply": has_easy_apply,
                            })

                    except Exception as e:
                        logger.warning(
                            f"[linkedin_applicator] Failed to parse job card: {e}"
                        )

                logger.info(
                    f"[linkedin_applicator] search_jobs: found {len(jobs)} Easy Apply jobs"
                )

            except CaptchaDetectedError:
                raise
            except Exception as e:
                logger.exception(f"[linkedin_applicator] search_jobs inner error: {e}")
            finally:
                await browser.close()

    except CaptchaDetectedError:
        raise
    except Exception as e:
        logger.exception(f"[linkedin_applicator] search_jobs outer error: {e}")

    return jobs


async def apply_to_job(
    email: str,
    password: str,
    job_url: str,
    user_profile: Dict,
    resume_pdf_path: str,
) -> Dict:
    """
    Apply to a single LinkedIn job using Easy Apply.
    user_profile keys: name, email, phone, experience_years, current_title, etc.
    resume_pdf_path: absolute path to resume PDF file.

    Returns {"success": bool, "error": str|None, "job_url": str}
    """
    if not PLAYWRIGHT_AVAILABLE:
        return _not_available_result("apply_to_job")

    logger.info(f"[linkedin_applicator] apply_to_job: {job_url}")

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

                logger.info(f"[linkedin_applicator] Navigating to job: {job_url}")
                await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(random.uniform(2.0, 3.0))

                await _check_captcha(page)

                # Check for Easy Apply button
                if not await is_easy_apply(page):
                    logger.warning(
                        f"[linkedin_applicator] No Easy Apply button found at {job_url}"
                    )
                    return {
                        "success": False,
                        "error": "no_easy_apply_button",
                        "job_url": job_url,
                    }

                # Click Easy Apply
                await page.click('button.jobs-apply-button:has-text("Easy Apply")')
                await asyncio.sleep(random.uniform(1.5, 2.5))

                # Multi-step form handling
                max_steps = 10
                step = 0

                while step < max_steps:
                    step += 1
                    logger.debug(f"[linkedin_applicator] Easy Apply step {step}")

                    # Fill contact info fields if present
                    await _fill_contact_info(page, user_profile)

                    # Upload resume if a file upload is present
                    await _upload_resume(page, resume_pdf_path)

                    # Answer text/select questions with defaults
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
                        logger.info(
                            f"[linkedin_applicator] Application submitted for {job_url}"
                        )
                        return {"success": True, "error": None, "job_url": job_url}

                    # Check for Next / Continue / Review button
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
                            await page.wait_for_selector(
                                '.artdeco-modal', timeout=1500
                            )
                        except PWTimeout:
                            # Modal gone — consider it submitted
                            logger.info(
                                f"[linkedin_applicator] Modal closed, assuming success for {job_url}"
                            )
                            return {"success": True, "error": None, "job_url": job_url}
                        break

                logger.warning(
                    f"[linkedin_applicator] Reached max steps ({max_steps}) for {job_url}"
                )
                return {
                    "success": False,
                    "error": "max_steps_reached",
                    "job_url": job_url,
                }

            except CaptchaDetectedError as e:
                logger.warning(f"[linkedin_applicator] CAPTCHA detected: {e}")
                return {
                    "success": False,
                    "error": f"captcha_detected: {str(e)}",
                    "job_url": job_url,
                }
            except PWTimeout as e:
                logger.error(f"[linkedin_applicator] Playwright timeout: {e}")
                return {
                    "success": False,
                    "error": f"playwright_timeout: {str(e)}",
                    "job_url": job_url,
                }
            except Exception as e:
                logger.exception(f"[linkedin_applicator] apply_to_job inner error: {e}")
                return {
                    "success": False,
                    "error": f"unexpected_error: {str(e)}",
                    "job_url": job_url,
                }
            finally:
                await browser.close()

    except Exception as e:
        logger.exception(f"[linkedin_applicator] apply_to_job outer error: {e}")
        return {
            "success": False,
            "error": f"browser_error: {str(e)}",
            "job_url": job_url,
        }


async def _fill_contact_info(page, user_profile: Dict) -> None:
    """Fill in contact info fields if present on the current form step."""
    field_map = {
        'input[id*="phoneNumber"], input[aria-label*="Phone"]': (
            user_profile.get("phone", "")
        ),
        'input[id*="firstName"], input[aria-label*="First name"]': (
            _get_first_name(user_profile.get("name", ""))
        ),
        'input[id*="lastName"], input[aria-label*="Last name"]': (
            _get_last_name(user_profile.get("name", ""))
        ),
        'input[id*="email"], input[aria-label*="Email"]': (
            user_profile.get("email", "")
        ),
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
        except Exception as e:
            logger.debug(f"[linkedin_applicator] _fill_contact_info field error: {e}")


async def _upload_resume(page, resume_pdf_path: str) -> None:
    """Upload resume PDF to file input if present."""
    if not resume_pdf_path:
        return
    try:
        import os
        if not os.path.exists(resume_pdf_path):
            logger.warning(
                f"[linkedin_applicator] Resume file not found: {resume_pdf_path}"
            )
            return
        file_input = await page.query_selector('input[type="file"]')
        if file_input:
            await file_input.set_input_files(resume_pdf_path)
            await asyncio.sleep(random.uniform(1.0, 2.0))
            logger.debug(
                f"[linkedin_applicator] Uploaded resume: {resume_pdf_path}"
            )
    except Exception as e:
        logger.warning(f"[linkedin_applicator] _upload_resume error: {e}")


async def _fill_form_defaults(page, user_profile: Dict) -> None:
    """Fill text questions and select elements with sensible defaults."""
    experience_years = str(user_profile.get("experience_years", "1"))

    # Fill any empty text inputs with a generic answer
    try:
        text_inputs = await page.query_selector_all(
            'input[type="text"]:not([aria-label*="ame"]):not([aria-label*="hone"])'
            ':not([aria-label*="mail"])'
        )
        for inp in text_inputs:
            try:
                val = await inp.input_value()
                if not val:
                    # Use experience years for numeric-looking fields
                    placeholder = await inp.get_attribute("placeholder") or ""
                    if any(kw in placeholder.lower() for kw in ["year", "лет", "опыт"]):
                        await inp.fill(experience_years)
                    else:
                        await inp.fill(experience_years)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"[linkedin_applicator] _fill_form_defaults text inputs error: {e}")

    # Handle select elements
    try:
        selects = await page.query_selector_all("select")
        for sel in selects:
            try:
                current = await sel.input_value()
                if not current or current == "Select an option":
                    # Pick first non-empty option
                    options = await sel.query_selector_all("option")
                    for opt in options:
                        val = await opt.get_attribute("value") or ""
                        if val and val not in ("", "Select an option"):
                            await sel.select_option(value=val)
                            break
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"[linkedin_applicator] _fill_form_defaults selects error: {e}")


def _get_first_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return parts[0] if parts else ""


def _get_last_name(full_name: str) -> str:
    parts = full_name.strip().split()
    return " ".join(parts[1:]) if len(parts) > 1 else ""


async def run_application_session(
    email: str,
    password: str,
    jobs: List[Dict],
    user_profile: Dict,
    resume_pdf_path: str,
) -> List[Dict]:
    """
    Run a full application session for a list of jobs.
    Respects MAX_APPS_PER_SESSION and 2-3 minute delays between applications.
    Returns list of result dicts.
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("[linkedin_applicator] run_application_session: Playwright not installed")
        return [_not_available_result("run_application_session")]

    results = []
    applied_count = 0

    for job in jobs:
        if applied_count >= MAX_APPS_PER_SESSION:
            logger.info(
                f"[linkedin_applicator] Reached session limit ({MAX_APPS_PER_SESSION}). Stopping."
            )
            break

        job_url = job.get("url", "")
        if not job_url:
            logger.warning("[linkedin_applicator] Job has no URL, skipping")
            continue

        result = await apply_to_job(
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
                f"[linkedin_applicator] Applied {applied_count}/{MAX_APPS_PER_SESSION}: "
                f"{job.get('title')} @ {job.get('company')}"
            )
        else:
            error = result.get("error", "")
            if "captcha_detected" in error:
                logger.warning(
                    "[linkedin_applicator] CAPTCHA detected — pausing session"
                )
                break

        # 2–3 minute delay between applications
        if applied_count < MAX_APPS_PER_SESSION and jobs.index(job) < len(jobs) - 1:
            delay = random.uniform(120, 180)
            logger.info(
                f"[linkedin_applicator] Waiting {delay:.0f}s before next application..."
            )
            await asyncio.sleep(delay)

    logger.info(
        f"[linkedin_applicator] Session complete. Applied: {applied_count}, "
        f"Results: {len(results)}"
    )
    return results
