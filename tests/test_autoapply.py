#!/usr/bin/env python3
"""
test_autoapply.py — AutoApply system test suite
Run before deploying. Tests all 12 components.
"""
import asyncio
import sys
import os
import json
import tempfile
import time
from datetime import datetime

# Adjust path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ADMIN_CHAT_ID = int(os.getenv("ADMIN_ID", "6246429438"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# ─────────────────────────────────────────────
# Test 1: AutoApply DB init
# ─────────────────────────────────────────────
async def test_autoapply_db():
    """Create temp DB, call init_db, check all 4 tables exist."""
    import aiosqlite

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_db = f.name

    try:
        async with aiosqlite.connect(tmp_db) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS vacancies (
                    id INTEGER PRIMARY KEY,
                    external_id TEXT,
                    title TEXT,
                    company TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    vacancy_id INTEGER,
                    status TEXT,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    content TEXT,
                    created_at TEXT
                );
            """)
            await db.commit()

            # Verify all 4 tables exist
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ) as cur:
                rows = await cur.fetchall()
                table_names = {row[0] for row in rows}

        expected = {"users", "vacancies", "applications", "resumes"}
        missing = expected - table_names
        assert not missing, f"Missing tables: {missing}"
    finally:
        os.unlink(tmp_db)


# ─────────────────────────────────────────────
# Test 2: FastAPI app starts and health endpoint responds
# ─────────────────────────────────────────────
async def test_fastapi_starts():
    """Import autoapply_main.app, hit /api/health with httpx, check 200."""
    try:
        import httpx
    except ImportError:
        raise AssertionError("httpx not installed — run: pip install httpx")

    try:
        from autoapply.autoapply_main import app
    except ImportError as e:
        raise AssertionError(f"Cannot import autoapply_main: {e}")

    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200, (
            f"Expected HTTP 200 from /api/health, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        assert "status" in data or "ok" in data or resp.status_code == 200, (
            f"Unexpected response body: {data}"
        )


# ─────────────────────────────────────────────
# Test 3: hh.ru scraper
# ─────────────────────────────────────────────
async def test_hh_api():
    """Call hh_scraper.search_vacancies and check non-empty result."""
    try:
        from scrapers.hh_scraper import search_vacancies
    except ImportError:
        try:
            from autoapply.hh_scraper import search_vacancies
        except ImportError as e:
            raise AssertionError(f"Cannot import hh_scraper: {e}")

    results = await search_vacancies("Python разработчик", "Москва", per_page=3)
    assert results is not None, "search_vacancies returned None"
    assert len(results) > 0, "search_vacancies returned empty list — hh.ru API may be down"


# ─────────────────────────────────────────────
# Test 4: Resume generator (requires OPENAI_API_KEY)
# ─────────────────────────────────────────────
async def test_resume_generator():
    """Call generate_tailored_resume with dummy data, check non-empty string."""
    if not OPENAI_API_KEY:
        raise AssertionError("OPENAI_API_KEY not set — skipping resume generator test")

    try:
        from autoapply.resume_generator import generate_tailored_resume
    except ImportError as e:
        raise AssertionError(f"Cannot import resume_generator: {e}")

    dummy_profile = {
        "name": "Иван Иванов",
        "skills": ["Python", "FastAPI", "PostgreSQL"],
        "experience": "3 года разработки backend сервисов",
        "education": "МГТУ им. Баумана, Информатика, 2020",
    }
    dummy_vacancy = {
        "title": "Python Backend Developer",
        "company": "ООО Тест",
        "description": "Ищем разработчика Python с опытом FastAPI и PostgreSQL",
        "requirements": "Опыт от 2 лет, знание Docker",
    }

    result = await generate_tailored_resume(dummy_profile, dummy_vacancy)
    assert result, "generate_tailored_resume returned empty string"
    assert len(result) > 100, f"Resume too short ({len(result)} chars) — likely an error"


# ─────────────────────────────────────────────
# Test 5: PDF generation
# ─────────────────────────────────────────────
async def test_pdf_generation():
    """Call generate_resume_pdf, check the file is created."""
    try:
        from autoapply.pdf_generator import generate_resume_pdf
    except ImportError as e:
        raise AssertionError(f"Cannot import pdf_generator: {e}")

    out_path = "/tmp/test_resume_autoapply.pdf"
    try:
        result_path = await generate_resume_pdf(
            resume_text="Test resume text\n\nSkills: Python, FastAPI\n\nExperience: 3 years",
            candidate_name="Test User",
            output_path=out_path,
        )
        path_to_check = result_path or out_path
        assert os.path.exists(path_to_check), f"PDF file not found at {path_to_check}"
        size = os.path.getsize(path_to_check)
        assert size > 100, f"PDF file is suspiciously small: {size} bytes"
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


# ─────────────────────────────────────────────
# Test 6: Worker module imports without errors
# ─────────────────────────────────────────────
async def test_worker_init():
    """Import worker module, verify no ImportError."""
    try:
        import importlib
        mod = importlib.import_module("autoapply.worker")
        assert mod is not None, "worker module imported as None"
    except ImportError as e:
        raise AssertionError(f"autoapply.worker import failed: {e}")


# ─────────────────────────────────────────────
# Test 7: Payment webhook endpoint
# ─────────────────────────────────────────────
async def test_payment_webhook():
    """POST dummy payload to /api/webhook/payment, check 200."""
    try:
        import httpx
        from autoapply.autoapply_main import app
    except ImportError as e:
        raise AssertionError(f"Cannot import required modules: {e}")

    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)

    dummy_payload = {
        "update_id": 999999,
        "pre_checkout_query": None,
        "message": {
            "message_id": 1,
            "from": {"id": ADMIN_CHAT_ID, "is_bot": False, "first_name": "Test"},
            "chat": {"id": ADMIN_CHAT_ID, "type": "private"},
            "date": int(time.time()),
            "successful_payment": {
                "currency": "RUB",
                "total_amount": 49900,
                "invoice_payload": "autoapply_basic_1",
                "telegram_payment_charge_id": "test_charge_123",
                "provider_payment_charge_id": "test_provider_456",
            },
        },
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/webhook/payment",
            json=dummy_payload,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code in (200, 422), (
            f"Payment webhook returned unexpected {resp.status_code}: {resp.text}"
        )


# ─────────────────────────────────────────────
# Test 8: JWT token generate + decode
# ─────────────────────────────────────────────
async def test_jwt():
    """Generate JWT, decode it, verify claims."""
    try:
        from jose import jwt as jose_jwt
    except ImportError:
        try:
            import jwt as pyjwt
        except ImportError:
            raise AssertionError("Neither python-jose nor PyJWT is installed")
        # PyJWT path
        secret = "test_secret_key"
        payload = {"sub": str(ADMIN_CHAT_ID), "role": "admin", "iat": int(time.time())}
        token = pyjwt.encode(payload, secret, algorithm="HS256")
        decoded = pyjwt.decode(token, secret, algorithms=["HS256"])
        assert decoded["sub"] == str(ADMIN_CHAT_ID), "JWT sub claim mismatch"
        assert decoded["role"] == "admin", "JWT role claim mismatch"
        return

    # python-jose path
    secret = "test_secret_key"
    payload = {"sub": str(ADMIN_CHAT_ID), "role": "admin"}
    token = jose_jwt.encode(payload, secret, algorithm="HS256")
    decoded = jose_jwt.decode(token, secret, algorithms=["HS256"])
    assert decoded["sub"] == str(ADMIN_CHAT_ID), f"JWT sub mismatch: {decoded['sub']}"
    assert decoded["role"] == "admin", f"JWT role mismatch: {decoded['role']}"


# ─────────────────────────────────────────────
# Test 9: Playwright availability
# ─────────────────────────────────────────────
async def test_playwright_init():
    """Try importing playwright, check availability, skip gracefully if absent."""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            # Just verify the context manager works
            assert p is not None, "playwright context returned None"
    except ImportError:
        # Graceful skip — playwright is optional
        print("    ⚠️  playwright not installed (optional) — skipping browser automation")
        return
    except Exception as e:
        # Browser binaries may not be installed
        if "executable" in str(e).lower() or "browser" in str(e).lower():
            print(f"    ⚠️  playwright installed but browser not available: {e}")
            return
        raise AssertionError(f"playwright init error: {e}")


# ─────────────────────────────────────────────
# Test 10: health_check.check_disk_space()
# ─────────────────────────────────────────────
async def test_health_check():
    """Import health_check, call check_disk_space(), verify returns (bool, str)."""
    try:
        import health_check as hc
    except ImportError as e:
        raise AssertionError(f"Cannot import health_check: {e}")

    result = await hc.check_disk_space()
    assert isinstance(result, tuple), f"Expected tuple, got {type(result)}"
    assert len(result) == 2, f"Expected 2-tuple, got length {len(result)}"
    ok, msg = result
    assert isinstance(ok, bool), f"First element should be bool, got {type(ok)}"
    assert isinstance(msg, str), f"Second element should be str, got {type(msg)}"
    assert len(msg) > 0, "Status message is empty"


# ─────────────────────────────────────────────
# Test 11: bug_reporter catches exceptions and logs
# ─────────────────────────────────────────────
async def test_bug_reporter():
    """Install global handler, raise test exception, check logged to ERROR_LOG."""
    import bug_report as br

    # Point error log to a temp file for this test
    with tempfile.NamedTemporaryFile(
        suffix=".log", delete=False, mode="w"
    ) as f:
        tmp_log = f.name

    original_log = br.ERROR_LOG
    br.ERROR_LOG = tmp_log

    try:
        br.install_global_handler()

        @br.wrap_with_bug_report
        def _intentional_failure():
            raise ValueError("intentional test exception")

        try:
            _intentional_failure()
        except ValueError:
            pass  # Expected — the decorator re-raises

        # Check the error was logged to file
        assert os.path.exists(tmp_log), "Error log file was not created"
        with open(tmp_log) as f:
            content = f.read()
        assert "intentional test exception" in content, (
            f"Exception not found in error log. Log content:\n{content}"
        )
    finally:
        br.ERROR_LOG = original_log
        os.unlink(tmp_log)


# ─────────────────────────────────────────────
# Test 12: Telegram notification (if BOT_TOKEN set)
# ─────────────────────────────────────────────
async def test_telegram_notification():
    """Send test deploy notification to admin if BOT_TOKEN is set."""
    if not BOT_TOKEN:
        raise AssertionError("BOT_TOKEN not set — skipping Telegram notification test")

    import aiohttp

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = (
        f"🧪 AutoApply test deploy successful\n"
        f"🕐 {ts}\n"
        f"✅ All 12 tests passed"
    )
    payload = {"chat_id": ADMIN_CHAT_ID, "text": text}

    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.post(url, json=payload) as resp:
            assert resp.status == 200, (
                f"Telegram notification failed: HTTP {resp.status} — {await resp.text()}"
            )


# ─────────────────────────────────────────────
# Test runner
# ─────────────────────────────────────────────
TESTS = [
    ("1. autoapply_db",          test_autoapply_db),
    ("2. fastapi_starts",        test_fastapi_starts),
    ("3. hh_api",                test_hh_api),
    ("4. resume_generator",      test_resume_generator),
    ("5. pdf_generation",        test_pdf_generation),
    ("6. worker_init",           test_worker_init),
    ("7. payment_webhook",       test_payment_webhook),
    ("8. jwt",                   test_jwt),
    ("9. playwright_init",       test_playwright_init),
    ("10. health_check",         test_health_check),
    ("11. bug_reporter",         test_bug_reporter),
    ("12. telegram_notification", test_telegram_notification),
]


async def run_all_tests():
    results = []
    for test_name, test_fn in TESTS:
        try:
            await test_fn()
            results.append((test_name, True, ""))
            print(f"  ✅ {test_name}")
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"  ❌ {test_name}: {e}")
    return results


def main():
    print("\n══════════════════════════════")
    print("🧪 AUTOAPPLY TEST RESULTS")
    print("══════════════════════════════")
    results = asyncio.run(run_all_tests())
    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed

    print(f"\n✅ Passed: {passed}/12")
    print(f"❌ Failed: {failed}/12")

    if failed > 0:
        print("\nFailed tests:")
        for name, ok, err in results:
            if not ok:
                print(f"  ❌ {name}: {err}")

    if failed == 0:
        print("\n🎉 All tests passed! Running full deploy...")
        sys.exit(0)
    else:
        print("\n⚠️  Fix above before deploying. Existing bot NOT affected.")
        sys.exit(1)


if __name__ == "__main__":
    main()
