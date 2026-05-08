"""
Tests for the Telegram→AutoApply SSO link token system.

Covers:
  - Valid token issues and verifies correctly
  - Expired token is rejected
  - Tampered token is rejected
  - One-time use (JTI replay) enforced via used_link_jti table
"""
import asyncio
import os
import tempfile
import time

import pytest

# Ensure LINK_SECRET is set before importing the crypto module
_TEST_SECRET = "test-secret-for-unit-tests-only"
os.environ.setdefault("LINK_SECRET", _TEST_SECRET)

from autoapply.crypto import issue_link_token, verify_link_token


# ── Token issue / verify ──────────────────────────────────────────────────────

class TestLinkToken:
    def test_issue_and_verify_roundtrip(self):
        token = issue_link_token(telegram_id=123456, secret=_TEST_SECRET)
        payload = verify_link_token(token, _TEST_SECRET)
        assert payload is not None
        assert payload["tid"] == 123456
        assert "jti" in payload
        assert payload["exp"] > int(time.time())

    def test_wrong_secret_rejected(self):
        token = issue_link_token(telegram_id=999, secret=_TEST_SECRET)
        assert verify_link_token(token, "wrong-secret") is None

    def test_tampered_payload_rejected(self):
        import base64, json
        token = issue_link_token(telegram_id=42, secret=_TEST_SECRET)
        payload_b64, sig = token.rsplit(".", 1)
        # Flip telegram_id in the payload
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        payload["tid"] = 9999
        bad_b64 = base64.urlsafe_b64encode(json.dumps(payload, separators=(",",":")).encode()).decode()
        bad_token = f"{bad_b64}.{sig}"
        assert verify_link_token(bad_token, _TEST_SECRET) is None

    def test_expired_token_rejected(self, monkeypatch):
        # Issue a token then advance time past TTL
        token = issue_link_token(telegram_id=1, secret=_TEST_SECRET)
        monkeypatch.setattr("time.time", lambda: time.time() + 400)  # 6+ min ahead
        assert verify_link_token(token, _TEST_SECRET) is None

    def test_missing_secret_raises(self):
        with pytest.raises(ValueError):
            issue_link_token(telegram_id=1, secret="")

    def test_empty_token_rejected(self):
        assert verify_link_token("", _TEST_SECRET) is None

    def test_malformed_token_rejected(self):
        assert verify_link_token("notavalidtoken", _TEST_SECRET) is None


# ── JTI one-time use ─────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_db(tmp_path):
    """Initialise a fresh autoapply DB for each test."""
    import asyncio
    db_path = str(tmp_path / "test_autoapply.db")

    async def _init():
        from autoapply.autoapply_db import init_db
        await init_db(db_path)

    asyncio.get_event_loop().run_until_complete(_init())
    return db_path


class TestJtiOneTimeUse:
    def test_first_consumption_succeeds(self, tmp_db):
        from autoapply.autoapply_db import consume_link_jti

        async def run():
            result = await consume_link_jti("unique-jti-abc", tmp_db)
            return result

        assert asyncio.get_event_loop().run_until_complete(run()) is True

    def test_replay_is_rejected(self, tmp_db):
        from autoapply.autoapply_db import consume_link_jti

        async def run():
            jti = "replay-jti-xyz"
            first = await consume_link_jti(jti, tmp_db)
            second = await consume_link_jti(jti, tmp_db)
            return first, second

        first, second = asyncio.get_event_loop().run_until_complete(run())
        assert first is True
        assert second is False

    def test_different_jtis_independent(self, tmp_db):
        from autoapply.autoapply_db import consume_link_jti

        async def run():
            a = await consume_link_jti("jti-aaa", tmp_db)
            b = await consume_link_jti("jti-bbb", tmp_db)
            return a, b

        a, b = asyncio.get_event_loop().run_until_complete(run())
        assert a is True
        assert b is True


# ── Full SSO flow: find-or-create autoapply user ──────────────────────────────

class TestFindOrCreateTelegramUser:
    def test_creates_user_on_first_link(self, tmp_db):
        from autoapply.autoapply_db import (
            get_autoapply_user_by_telegram,
            create_telegram_user,
            upsert_user_link,
        )

        async def run():
            tid = 777777
            user = await get_autoapply_user_by_telegram(tid, tmp_db)
            assert user is None  # not yet created

            user_id = await create_telegram_user(tid, tmp_db)
            assert isinstance(user_id, int)

            await upsert_user_link(tid, user_id, tmp_db)

            user = await get_autoapply_user_by_telegram(tid, tmp_db)
            assert user is not None
            assert user["telegram_id"] == tid
            assert user["email"] == f"tg_{tid}@tg.autoapply"
            return user

        asyncio.get_event_loop().run_until_complete(run())

    def test_upsert_link_is_idempotent(self, tmp_db):
        from autoapply.autoapply_db import create_telegram_user, upsert_user_link

        async def run():
            tid = 888888
            uid = await create_telegram_user(tid, tmp_db)
            await upsert_user_link(tid, uid, tmp_db)
            await upsert_user_link(tid, uid, tmp_db)  # second call must not raise

        asyncio.get_event_loop().run_until_complete(run())
