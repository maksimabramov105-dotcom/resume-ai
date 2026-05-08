"""Tests for P07 applications hub — 3 statuses, filters, actions."""
import asyncio
import os
import sys

import pytest
from fastapi.testclient import TestClient

# ── Env setup (must happen before any autoapply import) ───────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

_TEST_LOGS_DIR = "/tmp/hub_test_logs"
os.makedirs(_TEST_LOGS_DIR, exist_ok=True)

os.environ.setdefault("JWT_SECRET", "test-secret-hub-tests")
os.environ.setdefault("LINK_SECRET", "test-link-secret-hub")
os.environ.setdefault("AUTOAPPLY_DB", ":memory:")
os.environ.setdefault("LOGS_DIR", _TEST_LOGS_DIR)
os.environ.setdefault("BOT_DB", "/tmp/hub_test_bot.db")

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def tmp_db(tmp_path_factory):
    """Initialise a fresh autoapply DB shared across the module."""
    db_path = str(tmp_path_factory.mktemp("db") / "hub_test.db")

    async def _init():
        from autoapply.autoapply_db import init_db
        await init_db(db_path)

    asyncio.get_event_loop().run_until_complete(_init())
    return db_path


@pytest.fixture(scope="module")
def test_user(tmp_db):
    """Create one test user, return the row dict."""
    async def _create():
        from autoapply.autoapply_db import create_user, get_user_by_id
        uid = await create_user("hubtest@example.com", "!fakehash", db_path=tmp_db)
        return await get_user_by_id(uid, db_path=tmp_db)

    return asyncio.get_event_loop().run_until_complete(_create())


@pytest.fixture(scope="module")
def client(tmp_db, test_user):
    """TestClient with get_current_user overridden to return test_user."""
    import autoapply.autoapply_main as main_module

    # Point the app at our tmp db
    main_module.AUTOAPPLY_DB = tmp_db

    from autoapply.autoapply_main import app, get_current_user

    async def _mock_user():
        return test_user

    app.dependency_overrides[get_current_user] = _mock_user

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _insert_apps(tmp_db, user_id, rows):
    """Insert multiple application rows directly via DB helper."""
    async def _run():
        import aiosqlite
        from datetime import datetime
        async with aiosqlite.connect(tmp_db) as db:
            # We need a campaign first — use or create id=1
            await db.execute(
                "INSERT OR IGNORE INTO campaigns (id, user_id, job_title, status, created_at) "
                "VALUES (1, ?, 'Test Campaign', 'active', ?)",
                (user_id, datetime.utcnow().isoformat()),
            )
            ids = []
            for r in rows:
                cur = await db.execute(
                    """
                    INSERT INTO applications
                        (campaign_id, user_id, platform, vacancy_id, vacancy_title,
                         company_name, vacancy_url, resume_used, status, sent_at,
                         company_country, user_status, withdrawn_at)
                    VALUES (1, ?, ?, ?, ?, ?, '', '', ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        r.get("platform", "Adzuna"),
                        r.get("vacancy_id", f"v{len(ids)}"),
                        r.get("vacancy_title", "Software Engineer"),
                        r.get("company_name", "ACME Corp"),
                        r.get("status", "sent"),
                        r.get("sent_at", datetime.utcnow().isoformat()),
                        r.get("company_country", "US"),
                        r.get("user_status", "active"),
                        r.get("withdrawn_at", None),
                    ),
                )
                ids.append(cur.lastrowid)
            await db.commit()
        return ids

    return asyncio.get_event_loop().run_until_complete(_run())


# ── Test 1: GET /api/applications returns items and tab_counts ────────────────

class TestApplicationsList:
    def test_returns_items_and_tab_counts(self, client, tmp_db, test_user):
        from datetime import datetime
        _insert_apps(tmp_db, test_user["id"], [
            {"company_name": "AlphaInc", "user_status": "active", "vacancy_id": "t1a"},
            {"company_name": "BetaCorp", "user_status": "archived", "vacancy_id": "t1b"},
        ])
        resp = client.get("/api/applications")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "tab_counts" in body
        assert "active" in body["tab_counts"]
        assert "archived" in body["tab_counts"]
        assert "all" in body["tab_counts"]
        assert body["tab_counts"]["all"] >= 2


# ── Test 2: user_status filter ────────────────────────────────────────────────

class TestUserStatusFilter:
    def test_active_filter(self, client, tmp_db, test_user):
        _insert_apps(tmp_db, test_user["id"], [
            {"company_name": "ActiveCo", "user_status": "active", "vacancy_id": "t2a"},
        ])
        resp = client.get("/api/applications?user_status=active")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["user_status"] == "active" for i in items), \
            "All returned items should have user_status=active"

    def test_archived_filter(self, client, tmp_db, test_user):
        _insert_apps(tmp_db, test_user["id"], [
            {"company_name": "ArchivedCo", "user_status": "archived", "vacancy_id": "t2b"},
        ])
        resp = client.get("/api/applications?user_status=archived")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["user_status"] == "archived" for i in items), \
            "All returned items should have user_status=archived"


# ── Test 3: date_from / date_to filter ───────────────────────────────────────

class TestDateFilter:
    def test_date_range_narrows_results(self, client, tmp_db, test_user):
        _insert_apps(tmp_db, test_user["id"], [
            {"company_name": "OldCorp", "vacancy_id": "t3old", "sent_at": "2024-01-15T10:00:00"},
            {"company_name": "NewCorp", "vacancy_id": "t3new", "sent_at": "2026-03-20T10:00:00"},
        ])
        resp = client.get("/api/applications?date_from=2026-01-01&date_to=2026-12-31")
        assert resp.status_code == 200
        items = resp.json()["items"]
        companies = [i["company_name"] for i in items]
        assert "NewCorp" in companies
        assert "OldCorp" not in companies

    def test_invalid_date_returns_400(self, client):
        resp = client.get("/api/applications?date_from=not-a-date")
        assert resp.status_code == 400


# ── Test 4: free_text filter ──────────────────────────────────────────────────

class TestFreeTextFilter:
    def test_matches_company_name(self, client, tmp_db, test_user):
        _insert_apps(tmp_db, test_user["id"], [
            {"company_name": "UniqueXYZCorp", "vacancy_id": "t4a"},
            {"company_name": "SomethingElse", "vacancy_id": "t4b"},
        ])
        resp = client.get("/api/applications?free_text=UniqueXYZCorp")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(i["company_name"] == "UniqueXYZCorp" for i in items)
        assert not any(i["company_name"] == "SomethingElse" for i in items)

    def test_matches_vacancy_title(self, client, tmp_db, test_user):
        _insert_apps(tmp_db, test_user["id"], [
            {"vacancy_title": "DataScienceGuru", "company_name": "AnyCompany", "vacancy_id": "t4c"},
        ])
        resp = client.get("/api/applications?free_text=DataScienceGuru")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert any(i["vacancy_title"] == "DataScienceGuru" for i in items)


# ── Test 5: withdraw sets archived + withdrawn_at ────────────────────────────

class TestWithdraw:
    def test_withdraw_sets_archived_with_withdrawn_at(self, client, tmp_db, test_user):
        ids = _insert_apps(tmp_db, test_user["id"], [
            {"company_name": "WithdrawMe", "vacancy_id": "t5a", "user_status": "active"},
        ])
        app_id = ids[0]
        resp = client.post(f"/api/applications/{app_id}/withdraw")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["user_status"] == "archived"

        # Verify in DB
        async def _check():
            import aiosqlite
            async with aiosqlite.connect(tmp_db) as db:
                async with db.execute(
                    "SELECT user_status, withdrawn_at FROM applications WHERE id = ?", (app_id,)
                ) as cur:
                    return await cur.fetchone()

        row = asyncio.get_event_loop().run_until_complete(_check())
        assert row is not None
        assert row[0] == "archived"
        assert row[1] is not None  # withdrawn_at should be set


# ── Test 6: restore sets active ───────────────────────────────────────────────

class TestRestore:
    def test_restore_sets_active(self, client, tmp_db, test_user):
        ids = _insert_apps(tmp_db, test_user["id"], [
            {"company_name": "RestoreMe", "vacancy_id": "t6a", "user_status": "archived"},
        ])
        app_id = ids[0]
        resp = client.post(f"/api/applications/{app_id}/restore")
        assert resp.status_code == 200
        assert resp.json()["user_status"] == "active"

        async def _check():
            import aiosqlite
            async with aiosqlite.connect(tmp_db) as db:
                async with db.execute(
                    "SELECT user_status FROM applications WHERE id = ?", (app_id,)
                ) as cur:
                    return await cur.fetchone()

        row = asyncio.get_event_loop().run_until_complete(_check())
        assert row[0] == "active"


# ── Test 7: withdraw wrong owner → 404 ───────────────────────────────────────

class TestOwnershipGuard:
    def test_withdraw_wrong_owner_returns_404(self, client, tmp_db, test_user):
        # Insert an application for a different user_id (999)
        async def _insert_other():
            import aiosqlite
            from datetime import datetime
            async with aiosqlite.connect(tmp_db) as db:
                # Ensure user 999 exists as a campaign owner too
                await db.execute(
                    "INSERT OR IGNORE INTO autoapply_users "
                    "(id, email, password_hash, plan, created_at, last_active) "
                    "VALUES (999, 'other@test.com', '!hash', 'free', datetime('now'), datetime('now'))"
                )
                await db.execute(
                    "INSERT OR IGNORE INTO campaigns (id, user_id, job_title, status, created_at) "
                    "VALUES (999, 999, 'OtherCampaign', 'active', ?)",
                    (datetime.utcnow().isoformat(),),
                )
                cur = await db.execute(
                    "INSERT INTO applications "
                    "(campaign_id, user_id, platform, vacancy_id, vacancy_title, company_name, "
                    "vacancy_url, resume_used, status, sent_at) "
                    "VALUES (999, 999, 'Adzuna', 'other_vac', 'Dev', 'OtherCo', '', '', 'sent', ?)",
                    (datetime.utcnow().isoformat(),),
                )
                await db.commit()
                return cur.lastrowid

        other_id = asyncio.get_event_loop().run_until_complete(_insert_other())
        resp = client.post(f"/api/applications/{other_id}/withdraw")
        assert resp.status_code == 404


# ── Test 8: invalid user_status → 400 ────────────────────────────────────────

class TestValidation:
    def test_invalid_user_status_returns_400(self, client):
        resp = client.get("/api/applications?user_status=invalid")
        assert resp.status_code == 400

    def test_valid_user_status_active(self, client):
        resp = client.get("/api/applications?user_status=active")
        assert resp.status_code == 200

    def test_valid_user_status_archived(self, client):
        resp = client.get("/api/applications?user_status=archived")
        assert resp.status_code == 200


# ── Test 9: view-prefs GET / PUT roundtrip ────────────────────────────────────

class TestViewPrefs:
    def test_get_empty_prefs(self, client):
        resp = client.get("/api/user/view-prefs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_put_and_get_roundtrip(self, client):
        prefs = {"tab": "archived", "filtersOpen": "true", "country": "DE"}
        put_resp = client.put("/api/user/view-prefs", json=prefs)
        assert put_resp.status_code == 200
        assert put_resp.json()["ok"] is True

        get_resp = client.get("/api/user/view-prefs")
        assert get_resp.status_code == 200
        saved = get_resp.json()
        assert saved["tab"] == "archived"
        assert saved["country"] == "DE"

    def test_put_nested_value_returns_400(self, client):
        resp = client.put("/api/user/view-prefs", json={"bad": {"nested": "object"}})
        assert resp.status_code == 400

    def test_put_too_many_keys_returns_400(self, client):
        big = {f"key{i}": "v" for i in range(21)}
        resp = client.put("/api/user/view-prefs", json=big)
        assert resp.status_code == 400


# ── Test 10: pagination ───────────────────────────────────────────────────────

class TestPagination:
    def test_page_2_of_60_rows(self, client, tmp_db, test_user):
        # Insert 60 rows (there may already be some from other tests; we
        # count the total after insert and verify page arithmetic).
        rows = [
            {"company_name": f"PaginationCo{i}", "vacancy_id": f"pag_{i}"}
            for i in range(60)
        ]
        _insert_apps(tmp_db, test_user["id"], rows)

        resp1 = client.get("/api/applications?per_page=50&page=1")
        assert resp1.status_code == 200
        body1 = resp1.json()
        assert len(body1["items"]) == 50
        assert body1["pages"] >= 2

        resp2 = client.get("/api/applications?per_page=50&page=2")
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert len(body2["items"]) >= 1  # at least the overflow rows

        # Verify no overlap between pages
        ids1 = {i["id"] for i in body1["items"]}
        ids2 = {i["id"] for i in body2["items"]}
        assert ids1.isdisjoint(ids2), "Pages must not share the same row IDs"
