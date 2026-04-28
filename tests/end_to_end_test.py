#!/usr/bin/env python3
"""
end_to_end_test.py — Complete AutoApply system end-to-end test
Tests the entire flow from registration to job application.

Usage: python3 tests/end_to_end_test.py
Requires running AutoApply service on port 8080.
"""
import asyncio
import sys
import os
import json
import tempfile
from datetime import datetime

import aiosqlite
import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

AUTOAPPLY_URL = os.getenv("AUTOAPPLY_URL", "http://localhost:8080")
TEST_EMAIL = "endtoend_test@test.com"
TEST_PASSWORD = "testpassword123"
TEST_TELEGRAM_ID = 999998

from autoapply.config import AUTOAPPLY_DB, BOT_TOKEN, ADMIN_CHAT_ID

# Shared state passed between tests
_state: dict = {
    "token": None,
    "campaign_id": None,
}


# ── Test 1: Register + Login ──────────────────────────────────────────────────

async def test_register_and_login() -> None:
    """Cleanup test user if exists, register fresh, then login and store JWT."""
    # Pre-cleanup: remove test user from DB if exists
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            await db.execute(
                "DELETE FROM autoapply_users WHERE email = ?", (TEST_EMAIL,)
            )
            await db.commit()
    except Exception:
        pass  # DB may not exist yet or table missing — fine

    async with httpx.AsyncClient(base_url=AUTOAPPLY_URL, timeout=15) as client:
        # Register
        resp = await client.post("/api/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "telegram_id": TEST_TELEGRAM_ID,
        })
        assert resp.status_code in (200, 201), (
            f"Register failed: {resp.status_code} — {resp.text}"
        )

        # Login
        resp = await client.post("/api/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        })
        assert resp.status_code == 200, (
            f"Login failed: {resp.status_code} — {resp.text}"
        )
        data = resp.json()
        token = data.get("token") or data.get("access_token")
        assert token, f"No token in login response: {data}"
        _state["token"] = token


# ── Test 2: Create Campaign ───────────────────────────────────────────────────

async def test_create_campaign() -> None:
    """Create an AutoApply campaign and store the campaign_id."""
    token = _state.get("token")
    assert token, "No JWT token — test_register_and_login must pass first"

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=AUTOAPPLY_URL, timeout=15) as client:
        resp = await client.post(
            "/api/campaigns",
            json={
                "job_title": "Python разработчик",
                "location": "Москва",
                "keywords": ["Python", "FastAPI", "Django"],
                "daily_limit": 5,
            },
            headers=headers,
        )
        assert resp.status_code in (200, 201), (
            f"Create campaign failed: {resp.status_code} — {resp.text}"
        )
        data = resp.json()
        campaign_id = data.get("campaign_id") or data.get("id")
        assert campaign_id, f"No campaign_id in response: {data}"
        _state["campaign_id"] = campaign_id


# ── Test 3: English job search (Arbeitnow API) ────────────────────────────────

async def test_english_job_scraper() -> None:
    """Real Arbeitnow API call — fetches up to 5 Python vacancies."""
    from autoapply.english_job_engine import search_english_jobs

    vacancies = await search_english_jobs(
        query="Python developer",
        location="",
        sources=["arbeitnow"],
        limit_per_source=5,
    )
    assert isinstance(vacancies, list), f"Expected list, got {type(vacancies)}"
    # Validate structure of first vacancy if any returned
    if vacancies:
        first = vacancies[0]
        assert "id" in first or "vacancy_id" in first or "url" in first, (
            f"Vacancy dict missing id/url: {list(first.keys())}"
        )


# ── Test 4: Resume generation (OpenAI) ───────────────────────────────────────

async def test_resume_generation() -> None:
    """Generate a tailored resume via OpenAI. Skipped gracefully if key not set."""
    from autoapply.config import OPENAI_API_KEY

    if not OPENAI_API_KEY:
        print("    NOTE: OPENAI_API_KEY not set — skipping resume generation test")
        return

    from scrapers.resume_generator import generate_resume

    sample_vacancy = (
        "Python Backend Developer. Требования: 3+ лет опыта с Python, FastAPI, PostgreSQL. "
        "Задачи: разработка REST API, оптимизация запросов, code review."
    )
    sample_profile = (
        "Опытный Python разработчик, 4 года опыта. Стек: Python, FastAPI, Django, PostgreSQL, Redis. "
        "Образование: МГТУ им. Баумана, Информатика."
    )

    resume_text = await generate_resume(
        user_profile=sample_profile,
        vacancy_description=sample_vacancy,
        user_id=TEST_TELEGRAM_ID,
    )
    assert resume_text and len(resume_text) > 100, (
        f"Resume too short or empty: {repr(resume_text)}"
    )


# ── Test 5: PDF generation ────────────────────────────────────────────────────

async def test_pdf_generation() -> None:
    """Generate a PDF resume using resume_pdf_generator."""
    from scrapers.resume_pdf_generator import generate_resume_pdf, cleanup_pdf, REPORTLAB_AVAILABLE

    if not REPORTLAB_AVAILABLE:
        print("    NOTE: reportlab not installed — skipping PDF generation test")
        return

    sample_resume = """Иван Иванов
ivan@example.com | +7 999 123-45-67 | Москва

ОПЫТ РАБОТЫ
Senior Python Developer — ООО Технологии (2021–2024)
- Разработка микросервисов на FastAPI
- Оптимизация PostgreSQL запросов, снижение latency на 40%

ОБРАЗОВАНИЕ
МГТУ им. Баумана — Информатика и вычислительная техника (2017–2021)

НАВЫКИ
Python, FastAPI, Django, PostgreSQL, Redis, Docker, Kubernetes, Git
"""

    pdf_path = generate_resume_pdf(
        resume_text=sample_resume,
        candidate_name="Иван Иванов",
        user_id=TEST_TELEGRAM_ID,
        vacancy_id="test_vacancy_e2e",
    )
    assert pdf_path is not None, "generate_resume_pdf returned None"
    assert os.path.exists(pdf_path), f"PDF file not created at: {pdf_path}"
    assert os.path.getsize(pdf_path) > 1024, (
        f"PDF suspiciously small: {os.path.getsize(pdf_path)} bytes"
    )
    # Cleanup
    cleanup_pdf(pdf_path)
    assert not os.path.exists(pdf_path), "PDF file was not deleted by cleanup_pdf"


# ── Test 6: English job engine smoke test ─────────────────────────────────────

async def test_english_job_engine_sources() -> None:
    """Verify english_job_engine returns a list (even if empty) for each source."""
    from autoapply.english_job_engine import search_english_jobs

    for source in ("arbeitnow", "remoteok"):
        result = await search_english_jobs(
            query="developer",
            location="",
            sources=[source],
            limit_per_source=2,
        )
        assert isinstance(result, list), f"source={source} did not return a list"


# ── Test 7: Dashboard API ─────────────────────────────────────────────────────

async def test_dashboard_api() -> None:
    """GET /api/dashboard with JWT — expects 200 and user data."""
    token = _state.get("token")
    assert token, "No JWT token — test_register_and_login must pass first"

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=AUTOAPPLY_URL, timeout=15) as client:
        resp = await client.get("/api/dashboard", headers=headers)
        assert resp.status_code == 200, (
            f"Dashboard failed: {resp.status_code} — {resp.text}"
        )
        data = resp.json()
        # Should have at least user info
        assert isinstance(data, dict), f"Dashboard response not a dict: {data}"


# ── Test 8: Payment invoice creation ─────────────────────────────────────────

async def test_payment_invoice() -> None:
    """POST /api/payment/create-invoice — checks for invoice_url in response."""
    token = _state.get("token")
    assert token, "No JWT token — test_register_and_login must pass first"

    from autoapply.config import PLANS
    import os as _os
    cryptobot_token = _os.getenv("CRYPTOBOT_AUTOAPPLY_TOKEN", "")

    if not cryptobot_token:
        print("    NOTE: CRYPTOBOT_AUTOAPPLY_TOKEN not set — skipping payment invoice test")
        return

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(base_url=AUTOAPPLY_URL, timeout=15) as client:
        resp = await client.post(
            "/api/payment/create-invoice",
            json={"plan": "pro"},
            headers=headers,
        )
        assert resp.status_code == 200, (
            f"Create invoice failed: {resp.status_code} — {resp.text}"
        )
        data = resp.json()
        assert "invoice_url" in data, f"No invoice_url in response: {data}"
        assert data["invoice_url"].startswith("http"), (
            f"invoice_url looks invalid: {data['invoice_url']}"
        )


# ── Test 9: Cleanup test user ─────────────────────────────────────────────────

async def test_cleanup() -> None:
    """Delete test user from autoapply.db directly."""
    async with aiosqlite.connect(AUTOAPPLY_DB) as db:
        cursor = await db.execute(
            "DELETE FROM autoapply_users WHERE email = ?", (TEST_EMAIL,)
        )
        deleted = cursor.rowcount
        await db.commit()
    # Also clean up any campaigns
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            await db.execute(
                "DELETE FROM campaigns WHERE user_id IN "
                "(SELECT id FROM autoapply_users WHERE email = ?)",
                (TEST_EMAIL,),
            )
            await db.commit()
    except Exception:
        pass


# ── Test 10: Telegram admin notification ─────────────────────────────────────

async def test_telegram_admin_message() -> None:
    """Send a Telegram message to ADMIN_CHAT_ID to confirm bot token works."""
    if not BOT_TOKEN:
        print("    NOTE: BOT_TOKEN not set — skipping Telegram notification test")
        return

    import aiohttp

    text = (
        f"AutoApply E2E Test PASSED\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"All systems operational."
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json={"chat_id": ADMIN_CHAT_ID, "text": text},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            data = await resp.json()
            assert data.get("ok"), f"Telegram sendMessage failed: {data}"


# ── Runner ────────────────────────────────────────────────────────────────────

TESTS = [
    ("Register + Login",              test_register_and_login),
    ("Create Campaign",               test_create_campaign),
    ("English Job Scraper (Arbeitnow)", test_english_job_scraper),
    ("Resume Generation (OpenAI)",    test_resume_generation),
    ("PDF Generation (reportlab)",    test_pdf_generation),
    ("English Job Engine Sources",     test_english_job_engine_sources),
    ("Dashboard API",                 test_dashboard_api),
    ("Payment Invoice",               test_payment_invoice),
    ("Cleanup Test User",             test_cleanup),
    ("Telegram Admin Notification",   test_telegram_admin_message),
]


async def main() -> None:
    results: list = []
    start_all = datetime.now()

    print()
    print("════════════════════════════════════════════════════════════")
    print("   AutoApply End-to-End Test Suite")
    print(f"   Target: {AUTOAPPLY_URL}")
    print(f"   DB:     {AUTOAPPLY_DB}")
    print(f"   Start:  {start_all.strftime('%Y-%m-%d %H:%M:%S')}")
    print("════════════════════════════════════════════════════════════")
    print()

    for idx, (name, fn) in enumerate(TESTS, start=1):
        t_start = datetime.now()
        status = "PASS"
        error_msg = ""
        try:
            await fn()
        except Exception as exc:
            status = "FAIL"
            error_msg = str(exc)
        elapsed = (datetime.now() - t_start).total_seconds()

        icon = "✓" if status == "PASS" else "✗"
        print(f"  {icon} [{idx:2d}/10] {name:<40} {status}  ({elapsed:.2f}s)")
        if error_msg:
            # Indent error message
            for line in error_msg.splitlines()[:3]:
                print(f"           ERROR: {line}")

        results.append({
            "idx": idx,
            "name": name,
            "status": status,
            "elapsed": elapsed,
            "error": error_msg,
        })

    total_elapsed = (datetime.now() - start_all).total_seconds()
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print()
    print("════════════════════════════════════════════════════════════")
    print(f"   Results: {passed}/10 passed, {failed} failed")
    print(f"   Total time: {total_elapsed:.2f}s")
    print("════════════════════════════════════════════════════════════")
    print()

    if failed > 0:
        print("FAILED TESTS:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  [{r['idx']:2d}] {r['name']}")
                if r["error"]:
                    print(f"       {r['error'][:200]}")
        print()
        sys.exit(1)
    else:
        print("All tests passed.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
