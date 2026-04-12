"""
AutoApplyEngine — Playwright-based browser automation for job applications.
Supports hh.ru and SuperJob with human-like delays and rate limiting.
"""
from playwright.async_api import async_playwright
import asyncio, random, os, logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AutoApplyEngine:
    """Headless browser engine that applies to jobs AS THE USER."""

    def __init__(self):
        self.browser = None
        self.context = None
        self._pw = None

    async def start(self):
        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu']
        )
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU"
        )

    async def apply_hh_ru(self, user_email: str, user_password: str,
                           vacancy_ids: list, cover_letter_text: str = "") -> list:
        """Apply to multiple hh.ru vacancies using user's account."""
        page = await self.context.new_page()
        results = []

        try:
            # Login
            await page.goto("https://hh.ru/account/login", timeout=30000)
            await page.wait_for_timeout(random.randint(1000, 2000))
            await page.fill('input[name="login"]', user_email)
            await page.wait_for_timeout(random.randint(300, 700))
            await page.fill('input[name="password"]', user_password)
            await page.wait_for_timeout(random.randint(500, 1000))
            await page.click('button[data-qa="account-login-submit"]')
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.wait_for_timeout(random.randint(2000, 4000))

            # Check login success
            if "account/login" in page.url:
                logger.error("hh.ru login failed")
                return [{"status": "login_failed", "vacancy_id": vid} for vid in vacancy_ids]

            for vacancy_id in vacancy_ids:
                try:
                    await page.goto(f"https://hh.ru/vacancy/{vacancy_id}", timeout=20000)
                    await page.wait_for_timeout(random.randint(1500, 3000))

                    apply_btn = page.locator('a[data-qa="vacancy-response-link-top"]')
                    if await apply_btn.count() > 0:
                        await apply_btn.click()
                        await page.wait_for_timeout(random.randint(2000, 4000))

                        # Fill cover letter if field exists
                        letter_field = page.locator('textarea[data-qa="vacancy-response-popup-form-letter-input"]')
                        if await letter_field.count() > 0 and cover_letter_text:
                            await letter_field.fill(cover_letter_text[:1000])
                            await page.wait_for_timeout(random.randint(500, 1000))

                        submit_btn = page.locator('button[data-qa="vacancy-response-submit-popup"]')
                        if await submit_btn.count() > 0:
                            await submit_btn.click()
                            await page.wait_for_timeout(2000)
                            results.append({"vacancy_id": vacancy_id, "status": "applied", "ts": datetime.now().isoformat()})
                            logger.info(f"Applied hh.ru vacancy {vacancy_id}")
                        else:
                            results.append({"vacancy_id": vacancy_id, "status": "no_submit_button"})
                    else:
                        results.append({"vacancy_id": vacancy_id, "status": "already_applied_or_closed"})

                    # Rate limit: 5–15s between applications
                    await page.wait_for_timeout(random.randint(5000, 15000))

                except Exception as e:
                    logger.error(f"hh.ru apply error vacancy {vacancy_id}: {e}")
                    results.append({"vacancy_id": vacancy_id, "status": f"error: {str(e)}"})

        finally:
            await page.close()

        return results

    async def apply_superjob(self, user_email: str, user_password: str,
                              vacancy_urls: list) -> list:
        """Apply to SuperJob vacancies."""
        page = await self.context.new_page()
        results = []

        try:
            await page.goto("https://www.superjob.ru/auth/login/", timeout=30000)
            await page.wait_for_timeout(random.randint(1000, 2000))
            await page.fill('input[name="login"]', user_email)
            await page.fill('input[name="password"]', user_password)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.wait_for_timeout(random.randint(2000, 4000))

            for url in vacancy_urls:
                try:
                    await page.goto(url, timeout=20000)
                    await page.wait_for_timeout(random.randint(1500, 3000))
                    apply_btn = page.locator('button:has-text("Откликнуться")')
                    if await apply_btn.count() > 0:
                        await apply_btn.click()
                        await page.wait_for_timeout(3000)
                        results.append({"url": url, "status": "applied", "ts": datetime.now().isoformat()})
                    else:
                        results.append({"url": url, "status": "no_apply_button"})
                    await page.wait_for_timeout(random.randint(10000, 20000))
                except Exception as e:
                    results.append({"url": url, "status": f"error: {str(e)}"})
        finally:
            await page.close()

        return results

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self._pw:
            await self._pw.stop()


async def search_hh_jobs(query: str, area: int = 1, page: int = 0) -> dict:
    """Search hh.ru vacancies — NO auth required (public API)."""
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            "https://api.hh.ru/vacancies",
            params={"text": query, "area": area, "per_page": 100, "page": page},
            headers={"User-Agent": "ResumeAI/1.0 (max737books@gmail.com)"}
        )
        if r.status_code == 200:
            return r.json()
    return {"items": []}


async def get_hh_vacancy(vacancy_id: str) -> dict | None:
    """Get full vacancy details from hh.ru public API."""
    import httpx, re
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            f"https://api.hh.ru/vacancies/{vacancy_id}",
            headers={"User-Agent": "ResumeAI/1.0 (max737books@gmail.com)"}
        )
        if r.status_code == 200:
            data = r.json()
            desc_html = data.get("description", "")
            desc_text = re.sub(r'<[^>]+>', ' ', desc_html)
            desc_text = re.sub(r'\s+', ' ', desc_text).strip()[:3000]
            return {
                "id": vacancy_id,
                "title": data.get("name"),
                "company": data.get("employer", {}).get("name"),
                "salary": data.get("salary"),
                "description": desc_text,
                "skills": [s["name"] for s in data.get("key_skills", [])],
                "apply_url": data.get("alternate_url"),
                "area": data.get("area", {}).get("name"),
                "source": "hh.ru",
            }
    return None


def encrypt_credential(value: str) -> str:
    """Encrypt a credential using Fernet."""
    from cryptography.fernet import Fernet
    key = os.getenv("ENCRYPTION_KEY", "").encode()
    if not key:
        raise ValueError("ENCRYPTION_KEY not set")
    f = Fernet(key)
    return f.encrypt(value.encode()).decode()


def decrypt_credential(token: str) -> str:
    """Decrypt a Fernet-encrypted credential."""
    from cryptography.fernet import Fernet
    key = os.getenv("ENCRYPTION_KEY", "").encode()
    if not key:
        raise ValueError("ENCRYPTION_KEY not set")
    f = Fernet(key)
    return f.decrypt(token.encode()).decode()
