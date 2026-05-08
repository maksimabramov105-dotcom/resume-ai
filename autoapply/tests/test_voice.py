"""Tests for voice-AI resume pipeline (unit tests with mocked API calls).

Covers:
1. structure_transcript with mocked httpx → returns valid schema
2. transcribe with mocked httpx → returns transcript string
3. POST /api/resume/voice/transcribe with oversized file → 413
4. POST /api/resume/voice/build over-quota → 429
5. POST /api/resume/voice/build under-quota → 200 with resume_blob
"""
import asyncio
import io
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Minimal environment setup before any imports
_TEST_LOGS_DIR = "/tmp/voice_test_logs"
os.makedirs(_TEST_LOGS_DIR, exist_ok=True)

os.environ.setdefault("JWT_SECRET", "test-secret-voice-tests")
os.environ.setdefault("LINK_SECRET", "test-link-secret-voice")
os.environ.setdefault("AUTOAPPLY_DB", ":memory:")
os.environ.setdefault("LOGS_DIR", _TEST_LOGS_DIR)
os.environ.setdefault("BOT_DB", "/tmp/voice_test_bot.db")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_db(tmp_path):
    """Initialise a fresh autoapply DB for each test."""
    db_path = str(tmp_path / "test_voice.db")

    async def _init():
        from autoapply.autoapply_db import init_db
        await init_db(db_path)

    asyncio.get_event_loop().run_until_complete(_init())
    return db_path


@pytest.fixture()
def tmp_db_with_user(tmp_db):
    """DB with a pre-seeded free-plan user (id=1)."""
    async def _seed():
        import aiosqlite
        async with aiosqlite.connect(tmp_db) as db:
            await db.execute(
                "INSERT INTO autoapply_users (id, email, password_hash, plan, created_at, last_active, daily_limit, is_verified)"
                " VALUES (1, 'voice@test.com', 'x', 'free', '2026-01-01', '2026-01-01', 3, 1)"
            )
            await db.commit()

    asyncio.get_event_loop().run_until_complete(_seed())
    return tmp_db


@pytest.fixture()
def client(tmp_db_with_user):
    """TestClient with overridden get_current_user and AUTOAPPLY_DB pointing at tmp_db."""
    import autoapply.autoapply_main as _main
    from fastapi.testclient import TestClient

    # Override the DB path
    original_db = _main.AUTOAPPLY_DB
    _main.AUTOAPPLY_DB = tmp_db_with_user

    # Override get_current_user to return a fake free-plan user
    fake_user = {
        "id": 1,
        "email": "voice@test.com",
        "plan": "free",
        "applications_count": 0,
        "applications_limit": 3,
        "is_verified": 1,
    }

    async def _fake_get_current_user():
        return fake_user

    _main.app.dependency_overrides[_main.get_current_user] = _fake_get_current_user

    with TestClient(_main.app, raise_server_exceptions=False) as tc:
        yield tc

    _main.app.dependency_overrides.clear()
    _main.AUTOAPPLY_DB = original_db


# ── Unit tests: voice.py functions ───────────────────────────────────────────

class TestTranscribeFunction:
    def test_transcribe_returns_transcript(self):
        """transcribe() should call Whisper API and return transcript text."""
        from autoapply.services.voice import transcribe

        # Mock httpx.AsyncClient response
        mock_response = MagicMock()
        mock_response.json.return_value = {"text": "Hello my name is Alex Johnson and I am a Python developer."}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        async def _run():
            with patch("autoapply.services.voice.httpx.AsyncClient", return_value=mock_client):
                result = await transcribe(b"fake_audio_bytes", "recording.webm")
            return result

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result == "Hello my name is Alex Johnson and I am a Python developer."

    def test_transcribe_raises_without_api_key(self):
        """transcribe() should raise ValueError if OPENAI_API_KEY is missing."""
        from autoapply.services.voice import transcribe

        async def _run():
            with patch.dict(os.environ, {}, clear=False):
                saved = os.environ.pop("OPENAI_API_KEY", None)
                try:
                    with pytest.raises(ValueError, match="OPENAI_API_KEY required"):
                        await transcribe(b"audio", "test.webm")
                finally:
                    if saved is not None:
                        os.environ["OPENAI_API_KEY"] = saved

        asyncio.get_event_loop().run_until_complete(_run())


class TestStructureTranscriptFunction:
    def test_structure_transcript_returns_valid_schema(self):
        """structure_transcript() should return dict with required keys."""
        from autoapply.services.voice import structure_transcript

        sample_resume = {
            "name": "Alex Johnson",
            "headline": "Senior Python Developer",
            "summary": "Experienced developer with 6 years.",
            "experience": [
                {
                    "company": "DataTech Inc",
                    "position": "Senior Python Developer",
                    "period": "2021–2024",
                    "description": "• Built microservices\n• Reduced latency by 40%",
                }
            ],
            "education": [
                {
                    "institution": "State University",
                    "degree": "B.Sc. Computer Science",
                    "period": "2015–2019",
                }
            ],
            "skills": ["Python", "FastAPI", "Docker"],
            "languages": [{"language": "English", "level": "Native"}],
            "contact": {"email": "alex@example.com", "phone": "", "location": "Berlin", "linkedin": ""},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(sample_resume)}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        async def _run():
            with patch("autoapply.services.voice.httpx.AsyncClient", return_value=mock_client):
                result = await structure_transcript("My name is Alex Johnson, I am a Python developer.")
            return result

        result = asyncio.get_event_loop().run_until_complete(_run())

        assert isinstance(result, dict)
        assert result["name"] == "Alex Johnson"
        assert result["headline"] == "Senior Python Developer"
        assert isinstance(result["experience"], list)
        assert isinstance(result["skills"], list)
        assert isinstance(result["languages"], list)
        assert isinstance(result["contact"], dict)

    def test_structure_transcript_raises_on_empty_result(self):
        """structure_transcript() should raise ValueError when neither name nor headline is set."""
        from autoapply.services.voice import structure_transcript

        empty_resume = {
            "name": "",
            "headline": "",
            "summary": "",
            "experience": [],
            "education": [],
            "skills": [],
            "languages": [],
            "contact": {"email": "", "phone": "", "location": "", "linkedin": ""},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(empty_resume)}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        async def _run():
            with patch("autoapply.services.voice.httpx.AsyncClient", return_value=mock_client):
                with pytest.raises(ValueError, match="empty result"):
                    await structure_transcript("unclear mumbling...")

        asyncio.get_event_loop().run_until_complete(_run())

    def test_structure_transcript_strips_markdown_fences(self):
        """structure_transcript() should handle JSON wrapped in markdown code fences."""
        from autoapply.services.voice import structure_transcript

        sample_resume = {
            "name": "Jane Smith",
            "headline": "Product Manager",
            "summary": "PM with 5 years.",
            "experience": [],
            "education": [],
            "skills": ["Agile", "Jira"],
            "languages": [],
            "contact": {"email": "", "phone": "", "location": "", "linkedin": ""},
        }
        wrapped = f"```json\n{json.dumps(sample_resume)}\n```"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": wrapped}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        async def _run():
            with patch("autoapply.services.voice.httpx.AsyncClient", return_value=mock_client):
                result = await structure_transcript("My name is Jane Smith, I am a product manager.")
            return result

        result = asyncio.get_event_loop().run_until_complete(_run())
        assert result["name"] == "Jane Smith"


# ── Integration tests: API endpoints ─────────────────────────────────────────

class TestVoiceTranscribeEndpoint:
    def test_oversized_file_returns_413(self, client):
        """POST /api/resume/voice/transcribe with >5MB audio should return 413."""
        large_audio = b"x" * (5 * 1024 * 1024 + 1)  # 5MB + 1 byte

        response = client.post(
            "/api/resume/voice/transcribe",
            files={"audio": ("recording.webm", io.BytesIO(large_audio), "audio/webm")},
        )
        assert response.status_code == 413

    def test_missing_audio_field_returns_400(self, client):
        """POST /api/resume/voice/transcribe without audio field should return 400."""
        response = client.post("/api/resume/voice/transcribe", data={})
        assert response.status_code == 400

    def test_transcribe_success(self, client):
        """POST /api/resume/voice/transcribe with valid audio returns 200 with transcript."""
        small_audio = b"fake_webm_data_1234"

        mock_response = MagicMock()
        mock_response.json.return_value = {"text": "I am a software engineer with 5 years of experience."}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("autoapply.services.voice.httpx.AsyncClient", return_value=mock_client):
            response = client.post(
                "/api/resume/voice/transcribe",
                files={"audio": ("recording.webm", io.BytesIO(small_audio), "audio/webm")},
            )

        assert response.status_code == 200
        data = response.json()
        assert "transcript" in data
        assert data["transcript"] == "I am a software engineer with 5 years of experience."
        assert "duration_hint" in data


class TestVoiceBuildEndpoint:
    def test_over_quota_returns_429(self, client, tmp_db_with_user):
        """POST /api/resume/voice/build when quota exceeded should return 429."""
        import aiosqlite

        # Exhaust the free plan quota (1 per day) by inserting a prior voice_build log
        async def _exhaust():
            async with aiosqlite.connect(tmp_db_with_user) as db:
                await db.execute(
                    "INSERT INTO web_generations (user_id, type, created_at) VALUES (?, ?, datetime('now'))",
                    (1, "voice_build")
                )
                await db.commit()

        asyncio.get_event_loop().run_until_complete(_exhaust())

        # Override AUTOAPPLY_DB in the module being tested
        import autoapply.autoapply_main as _main
        original_db = _main.AUTOAPPLY_DB
        _main.AUTOAPPLY_DB = tmp_db_with_user

        try:
            response = client.post(
                "/api/resume/voice/build",
                json={"transcript": "I am Alex, a Python developer with 5 years of experience."},
            )
        finally:
            _main.AUTOAPPLY_DB = original_db

        assert response.status_code == 429

    def test_under_quota_returns_200_with_resume_blob(self, client, tmp_db_with_user):
        """POST /api/resume/voice/build under quota returns 200 with resume_blob."""
        import autoapply.autoapply_main as _main

        original_db = _main.AUTOAPPLY_DB
        _main.AUTOAPPLY_DB = tmp_db_with_user

        sample_resume = {
            "name": "Alex Johnson",
            "headline": "Python Developer",
            "summary": "5 years of experience.",
            "experience": [],
            "education": [],
            "skills": ["Python"],
            "languages": [{"language": "English", "level": "Native"}],
            "contact": {"email": "", "phone": "", "location": "", "linkedin": ""},
        }

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(sample_resume)}}]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        try:
            with patch("autoapply.services.voice.httpx.AsyncClient", return_value=mock_client):
                response = client.post(
                    "/api/resume/voice/build",
                    json={
                        "transcript": "My name is Alex Johnson, I am a Python developer with 5 years of experience.",
                        "save_to_portfolio": False,
                    },
                )
        finally:
            _main.AUTOAPPLY_DB = original_db

        assert response.status_code == 200
        data = response.json()
        assert "resume_blob" in data
        assert data["resume_blob"]["name"] == "Alex Johnson"
        assert data["resume_blob"]["headline"] == "Python Developer"
        assert "saved" in data
