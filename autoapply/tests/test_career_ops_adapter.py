"""
tests/test_career_ops_adapter.py — unit tests for career-ops adapter.

Design:
- _call_openai is mocked to return deterministic JSON.
- generate-pdf.mjs subprocess is mocked (stub writes a zero-byte file).
- Tests run in-process with a temporary aiosqlite DB.
- Country gate is tested: RU-domiciled vacancies must not produce DB rows.

Run:  pytest autoapply/tests/test_career_ops_adapter.py -v
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_vacancy(**overrides) -> dict:
    base = {
        "id": "v-test-001",
        "title": "Senior Python Engineer",
        "company": "Acme Corp",
        "location": "Remote, US",
        "url": "https://jobs.example.com/acme-senior-python",
        "description": "We need a senior Python engineer with FastAPI and asyncio experience.",
    }
    base.update(overrides)
    return base


def _make_user(**overrides) -> dict:
    base = {
        "id": 42,
        "email": "alice@example.com",
        "full_name": "Alice Example",
        "resume_text": "Senior Python engineer with 8 years experience. Expertise: FastAPI, asyncio, PostgreSQL.",
        "linkedin_password_enc": "MUST_NOT_LEAK",   # secret — must be stripped
        "password_hash": "MUST_NOT_LEAK",           # secret — must be stripped
    }
    base.update(overrides)
    return base


def _make_campaign(**overrides) -> dict:
    base = {
        "id": 1,
        "user_id": 42,
        "job_title": "Senior Python Engineer",
        "location": "Remote",
        "salary_min": 0,
        "experience": "",
        "platforms": ["all"],
        "daily_limit": 5,
        "engine": "career_ops",
    }
    base.update(overrides)
    return base


_STUB_SCORE_RESPONSE = json.dumps({
    "dimensions": {
        "skills_match": 8.5,
        "seniority_fit": 7.0,
        "role_alignment": 8.0,
        "location_fit": 9.0,
        "industry_fit": 7.5,
        "growth_potential": 7.0,
    },
    "composite_score": 7.8,
    "top_strengths": ["FastAPI experience", "asyncio expertise"],
    "key_gaps": ["No cloud infra mentioned"],
    "one_line_summary": "Strong match — Python/async skills align well with JD requirements.",
})


# ── score_vacancy tests ────────────────────────────────────────────────────────

class TestScoreVacancy(unittest.TestCase):
    def test_returns_composite_score(self):
        """score_vacancy returns a float 0-10 composite_score."""
        from autoapply.engines.career_ops_adapter import score_vacancy

        async def _run():
            with patch(
                "autoapply.engines.career_ops_adapter._call_openai",
                new=AsyncMock(return_value=_STUB_SCORE_RESPONSE),
            ):
                result = await score_vacancy(_make_vacancy(), _make_user())
            return result

        result = asyncio.run(_run())
        self.assertIn("composite_score", result)
        self.assertAlmostEqual(result["composite_score"], 7.8, places=1)
        self.assertIn("top_strengths", result)
        self.assertIsInstance(result["top_strengths"], list)

    def test_falls_back_on_api_error(self):
        """score_vacancy returns neutral 5.0 score when API call fails."""
        from autoapply.engines.career_ops_adapter import score_vacancy

        async def _run():
            with patch(
                "autoapply.engines.career_ops_adapter._call_openai",
                new=AsyncMock(side_effect=RuntimeError("API unavailable")),
            ):
                return await score_vacancy(_make_vacancy(), _make_user())

        result = asyncio.run(_run())
        self.assertEqual(result["composite_score"], 5.0)
        self.assertEqual(result["top_strengths"], [])

    def test_composite_score_clamped_to_0_10(self):
        """composite_score is clamped to [0, 10] even if LLM returns out-of-range."""
        from autoapply.engines.career_ops_adapter import score_vacancy

        stub_out_of_range = json.dumps({
            "composite_score": 15.0,  # out of range
            "dimensions": {},
            "top_strengths": [],
            "key_gaps": [],
            "one_line_summary": "oops",
        })

        async def _run():
            with patch(
                "autoapply.engines.career_ops_adapter._call_openai",
                new=AsyncMock(return_value=stub_out_of_range),
            ):
                return await score_vacancy(_make_vacancy(), _make_user())

        result = asyncio.run(_run())
        self.assertLessEqual(result["composite_score"], 10.0)


# ── secrets isolation ─────────────────────────────────────────────────────────

class TestSecretsIsolation(unittest.TestCase):
    def test_public_portfolio_strips_secrets(self):
        """_public_portfolio must not include linkedin_password_enc or password_hash."""
        from autoapply.engines.career_ops_adapter import _public_portfolio

        user = _make_user()
        pub = _public_portfolio(user)

        self.assertNotIn("linkedin_password_enc", pub)
        self.assertNotIn("password_hash", pub)
        self.assertIn("email", pub)
        self.assertIn("resume_text", pub)

    def test_score_vacancy_never_sees_secrets(self):
        """score_vacancy receives only the public portfolio; secrets must not appear in the prompt."""
        from autoapply.engines.career_ops_adapter import score_vacancy

        captured_prompts: list[str] = []

        async def _capture_openai(system: str, user: str, **_kw) -> str:
            captured_prompts.append(system + user)
            return _STUB_SCORE_RESPONSE

        async def _run():
            with patch(
                "autoapply.engines.career_ops_adapter._call_openai",
                new=AsyncMock(side_effect=_capture_openai),
            ):
                # Pass the full user including secrets
                return await score_vacancy(_make_vacancy(), _make_user())

        asyncio.run(_run())
        combined = " ".join(captured_prompts)
        self.assertNotIn("MUST_NOT_LEAK", combined)


# ── generate_cv_pdf tests ─────────────────────────────────────────────────────

class TestGenerateCvPdf(unittest.TestCase):
    def test_returns_none_when_node_missing(self):
        """generate_cv_pdf returns None gracefully if node is not in PATH."""
        from autoapply.engines.career_ops_adapter import generate_cv_pdf

        async def _run():
            with patch("shutil.which", return_value=None):
                return await generate_cv_pdf("<html></html>", 42, "acme", "v001")

        result = asyncio.run(_run())
        self.assertIsNone(result)

    def test_returns_path_on_success(self):
        """generate_cv_pdf returns the output path when node succeeds."""
        import subprocess

        from autoapply.engines.career_ops_adapter import CAREER_OPS_DIR, generate_cv_pdf

        async def _run():
            with tempfile.TemporaryDirectory() as tmpdir:
                expected_pdf = os.path.join(tmpdir, "test_user", "acme-v001.pdf")
                # Create the expected output dir/file as the stub would
                os.makedirs(os.path.dirname(expected_pdf), exist_ok=True)
                Path(expected_pdf).write_bytes(b"")  # stub PDF

                stub_result = MagicMock()
                stub_result.returncode = 0

                generate_script = os.path.join(CAREER_OPS_DIR, "generate-pdf.mjs")

                with (
                    patch("shutil.which", return_value="/usr/bin/node"),
                    patch("os.path.isfile", return_value=True),
                    patch("asyncio.to_thread", new=AsyncMock(return_value=stub_result)),
                    patch(
                        "autoapply.engines.career_ops_adapter.CV_STORE_DIR",
                        tmpdir,
                    ),
                ):
                    result = await generate_cv_pdf("<html></html>", 42, "acme", "v001")
                return result

        result = asyncio.run(_run())
        # Result should be a string path (may or may not exist in stub, but not None)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, str)


# ── run_batch E2E smoke test ──────────────────────────────────────────────────

class TestRunBatch(unittest.TestCase):
    """
    Smoke-tests run_batch() end-to-end with:
    - deterministic stub scoring (7.8 / 10)
    - mocked PDF generation (returns a fixed path)
    - real aiosqlite DB in a temp file
    - country gate: RU vacancy must be filtered out
    """

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._db_path = os.path.join(self._tmpdir, "test_autoapply.db")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _init_test_db(self):
        """Bootstrap a minimal autoapply.db for the test."""
        import aiosqlite

        async def _setup():
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS autoapply_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        plan TEXT DEFAULT 'free',
                        created_at TEXT,
                        last_active TEXT,
                        daily_limit INTEGER DEFAULT 3,
                        applications_today INTEGER DEFAULT 0,
                        applications_total INTEGER DEFAULT 0,
                        responses_received INTEGER DEFAULT 0,
                        linkedin_email TEXT, linkedin_password_enc TEXT,
                        resume_text TEXT
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS campaigns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        job_title TEXT NOT NULL,
                        location TEXT, salary_min INTEGER DEFAULT 0,
                        experience TEXT, platforms TEXT, daily_limit INTEGER,
                        engine TEXT DEFAULT 'api_boards',
                        status TEXT DEFAULT 'active',
                        created_at TEXT, applications_sent INTEGER DEFAULT 0,
                        responses INTEGER DEFAULT 0, last_run TEXT
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS applications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        campaign_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        platform TEXT, vacancy_id TEXT, vacancy_title TEXT,
                        company_name TEXT, vacancy_url TEXT, resume_used TEXT,
                        status TEXT DEFAULT 'sent',
                        sent_at TEXT, response_at TEXT,
                        company_country TEXT,
                        user_status TEXT DEFAULT 'active',
                        withdrawn_at TEXT, last_user_action_at TEXT,
                        engine TEXT DEFAULT 'api_boards',
                        cv_pdf_path TEXT, match_score REAL
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS vacancies_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        platform TEXT, vacancy_id TEXT UNIQUE,
                        title TEXT, company TEXT, location TEXT,
                        salary TEXT, description TEXT, url TEXT,
                        fetched_at TEXT, applied INTEGER DEFAULT 0
                    )
                """)
                # Insert test user
                await db.execute("""
                    INSERT INTO autoapply_users
                        (id, email, password_hash, plan, created_at, daily_limit)
                    VALUES (42, 'alice@example.com', 'hash', 'pro',
                            datetime('now'), 10)
                """)
                # Insert test campaign
                await db.execute("""
                    INSERT INTO campaigns
                        (id, user_id, job_title, platforms, engine,
                         daily_limit, status, created_at)
                    VALUES (1, 42, 'Senior Python Engineer', '["all"]',
                            'career_ops', 5, 'active', datetime('now'))
                """)
                await db.commit()

        asyncio.run(_setup())

    def test_batch_produces_pending_review_row(self):
        """
        run_batch with a passing vacancy produces a 'pending_review' application row
        with a non-null cv_pdf_path.
        """
        import aiosqlite

        from autoapply.engines.career_ops_adapter import run_batch

        self._init_test_db()

        stub_pdf_path = os.path.join(self._tmpdir, "cv", "42", "acme-corp-v-test-001.pdf")
        os.makedirs(os.path.dirname(stub_pdf_path), exist_ok=True)
        Path(stub_pdf_path).write_bytes(b"%PDF-stub")

        async def _run():
            with (
                patch(
                    "autoapply.engines.career_ops_adapter._call_openai",
                    new=AsyncMock(return_value=_STUB_SCORE_RESPONSE),
                ),
                patch(
                    "autoapply.engines.career_ops_adapter.generate_cv_pdf",
                    new=AsyncMock(return_value=stub_pdf_path),
                ),
            ):
                results = await run_batch(
                    campaign=_make_campaign(),
                    vacancies=[_make_vacancy()],
                    user=_make_user(),
                    db_path=self._db_path,
                )

            # Verify returned data
            assert len(results) == 1, f"Expected 1 result, got {len(results)}: {results}"
            r = results[0]
            assert r["status"] == "pending_review"
            assert r["cv_pdf_path"] == stub_pdf_path
            assert r["match_score"] == pytest.approx(7.8, abs=0.1)

            # Verify DB row
            async with aiosqlite.connect(self._db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM applications WHERE campaign_id = 1"
                ) as cur:
                    rows = await cur.fetchall()

            assert len(rows) == 1, "Expected exactly 1 DB row"
            row = dict(rows[0])
            assert row["status"] == "pending_review"
            assert row["engine"] == "career_ops"
            assert row["cv_pdf_path"] == stub_pdf_path
            assert row["match_score"] == pytest.approx(7.8, abs=0.1)

        asyncio.run(_run())

    def test_ru_vacancy_is_filtered_by_country_gate(self):
        """
        A vacancy with a Russian company location must be blocked by the country gate
        and must NOT appear as a pending_review row.
        """
        import aiosqlite

        from autoapply.engines.career_ops_adapter import run_batch

        self._init_test_db()

        ru_vacancy = _make_vacancy(
            id="v-ru-001",
            company="HeadHunter OOO",
            location="Moscow, Russia",
        )

        async def _run():
            with (
                patch(
                    "autoapply.engines.career_ops_adapter._call_openai",
                    new=AsyncMock(return_value=_STUB_SCORE_RESPONSE),
                ),
                patch(
                    "autoapply.engines.career_ops_adapter.generate_cv_pdf",
                    new=AsyncMock(return_value="/tmp/fake.pdf"),
                ),
            ):
                results = await run_batch(
                    campaign=_make_campaign(),
                    vacancies=[ru_vacancy],
                    user=_make_user(),
                    db_path=self._db_path,
                )

            # Blocked → empty results list
            assert results == [], f"Expected [] but got {results}"

            # Verify no DB row created
            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute(
                    "SELECT COUNT(*) FROM applications WHERE campaign_id = 1"
                ) as cur:
                    row = await cur.fetchone()
            assert row[0] == 0, "Expected 0 DB rows for RU-blocked vacancy"

        asyncio.run(_run())

    def test_below_threshold_vacancy_skipped(self):
        """Vacancies scoring below MIN_SCORE_FOR_PDF threshold produce no DB row."""
        import aiosqlite

        from autoapply.engines.career_ops_adapter import run_batch

        self._init_test_db()

        low_score_stub = json.dumps({
            "composite_score": 3.0,  # below threshold
            "dimensions": {},
            "top_strengths": [],
            "key_gaps": ["Almost no match"],
            "one_line_summary": "Poor fit",
        })

        async def _run():
            with (
                patch(
                    "autoapply.engines.career_ops_adapter._call_openai",
                    new=AsyncMock(return_value=low_score_stub),
                ),
                patch(
                    "autoapply.engines.career_ops_adapter.generate_cv_pdf",
                    new=AsyncMock(return_value="/tmp/fake.pdf"),
                ),
            ):
                results = await run_batch(
                    campaign=_make_campaign(),
                    vacancies=[_make_vacancy()],
                    user=_make_user(),
                    db_path=self._db_path,
                )

            assert results == []

            async with aiosqlite.connect(self._db_path) as db:
                async with db.execute(
                    "SELECT COUNT(*) FROM applications WHERE campaign_id = 1"
                ) as cur:
                    row = await cur.fetchone()
            assert row[0] == 0

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
