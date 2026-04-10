"""
autoapply_db.py — Async SQLite database module for AutoApply.
Uses aiosqlite. Never touches bot.db tables.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite

from autoapply.config import AUTOAPPLY_DB, PLANS

logger = logging.getLogger(__name__)

# ── Schema ────────────────────────────────────────────────────────────────────

_CREATE_AUTOAPPLY_USERS = """
CREATE TABLE IF NOT EXISTS autoapply_users (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id          INTEGER,
    email                TEXT    UNIQUE NOT NULL,
    password_hash        TEXT    NOT NULL,
    plan                 TEXT    DEFAULT 'free',
    created_at           TEXT,
    last_active          TEXT,
    daily_limit          INTEGER DEFAULT 3,
    applications_today   INTEGER DEFAULT 0,
    applications_total   INTEGER DEFAULT 0,
    responses_received   INTEGER DEFAULT 0,
    hh_token             TEXT,
    hh_resume_id         TEXT,
    linkedin_email       TEXT,
    linkedin_password_enc TEXT,
    resume_text          TEXT
)
"""

_CREATE_CAMPAIGNS = """
CREATE TABLE IF NOT EXISTS campaigns (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id            INTEGER NOT NULL REFERENCES autoapply_users(id),
    job_title          TEXT    NOT NULL,
    location           TEXT,
    salary_min         INTEGER DEFAULT 0,
    experience         TEXT,
    platforms          TEXT,
    daily_limit        INTEGER,
    status             TEXT    DEFAULT 'active',
    created_at         TEXT,
    applications_sent  INTEGER DEFAULT 0,
    responses          INTEGER DEFAULT 0,
    last_run           TEXT
)
"""

_CREATE_APPLICATIONS = """
CREATE TABLE IF NOT EXISTS applications (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id    INTEGER NOT NULL REFERENCES campaigns(id),
    user_id        INTEGER NOT NULL REFERENCES autoapply_users(id),
    platform       TEXT,
    vacancy_id     TEXT,
    vacancy_title  TEXT,
    company_name   TEXT,
    vacancy_url    TEXT,
    resume_used    TEXT,
    status         TEXT DEFAULT 'sent',
    sent_at        TEXT,
    response_at    TEXT
)
"""

_CREATE_VACANCIES_CACHE = """
CREATE TABLE IF NOT EXISTS vacancies_cache (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    platform    TEXT,
    vacancy_id  TEXT UNIQUE,
    title       TEXT,
    company     TEXT,
    location    TEXT,
    salary      TEXT,
    description TEXT,
    url         TEXT,
    fetched_at  TEXT,
    applied     INTEGER DEFAULT 0
)
"""

_CREATE_EMAIL_TOKENS = """
CREATE TABLE IF NOT EXISTS email_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES autoapply_users(id),
    token      TEXT UNIQUE NOT NULL,
    kind       TEXT NOT NULL,  -- 'verify' or 'reset'
    expires_at TEXT NOT NULL,
    used       INTEGER DEFAULT 0
)
"""

_MIGRATE_IS_VERIFIED = """
ALTER TABLE autoapply_users ADD COLUMN is_verified INTEGER DEFAULT 0
"""

# ── Init ─────────────────────────────────────────────────────────────────────

async def init_db(db_path: str = AUTOAPPLY_DB) -> None:
    """Create all AutoApply tables (IF NOT EXISTS). Never touches bot.db."""
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(_CREATE_AUTOAPPLY_USERS)
            await db.execute(_CREATE_CAMPAIGNS)
            await db.execute(_CREATE_APPLICATIONS)
            await db.execute(_CREATE_VACANCIES_CACHE)
            await db.execute(_CREATE_EMAIL_TOKENS)
            # Migration: add is_verified if column doesn't exist yet
            try:
                await db.execute(_MIGRATE_IS_VERIFIED)
            except Exception:
                pass  # column already exists
            await db.commit()
        logger.info("[autoapply_db] init_db: all tables ready at %s", db_path)
    except Exception as exc:
        logger.exception("[autoapply_db] init_db failed: %s", exc)
        raise


# ── Row helper ────────────────────────────────────────────────────────────────

def _row_to_dict(cursor: aiosqlite.Cursor, row) -> dict:
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


# ── User functions ────────────────────────────────────────────────────────────

async def get_user_by_email(email: str, db_path: str = AUTOAPPLY_DB) -> Optional[dict]:
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM autoapply_users WHERE email = ?", (email,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None
    except Exception as exc:
        logger.exception("[autoapply_db] get_user_by_email error: %s", exc)
        return None


async def get_user_by_id(user_id: int, db_path: str = AUTOAPPLY_DB) -> Optional[dict]:
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM autoapply_users WHERE id = ?", (user_id,)
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None
    except Exception as exc:
        logger.exception("[autoapply_db] get_user_by_id error: %s", exc)
        return None


async def create_user(
    email: str,
    password_hash: str,
    telegram_id: Optional[int] = None,
    db_path: str = AUTOAPPLY_DB,
) -> int:
    """Insert new user. Returns new user_id."""
    now = datetime.utcnow().isoformat()
    try:
        async with aiosqlite.connect(db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO autoapply_users
                    (telegram_id, email, password_hash, plan, created_at, last_active, daily_limit)
                VALUES (?, ?, ?, 'free', ?, ?, 3)
                """,
                (telegram_id, email, password_hash, now, now),
            )
            await db.commit()
            return cur.lastrowid
    except Exception as exc:
        logger.exception("[autoapply_db] create_user error: %s", exc)
        raise


async def update_user_last_active(user_id: int, db_path: str = AUTOAPPLY_DB) -> None:
    try:
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE autoapply_users SET last_active = ? WHERE id = ?",
                (now, user_id),
            )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] update_user_last_active error: %s", exc)


async def update_user_plan(user_id: int, plan: str, db_path: str = AUTOAPPLY_DB) -> None:
    """Upgrade user plan and adjust daily_limit accordingly."""
    try:
        daily_limit = PLANS.get(plan, {}).get("daily_limit", 3)
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE autoapply_users SET plan = ?, daily_limit = ? WHERE id = ?",
                (plan, daily_limit, user_id),
            )
            await db.commit()
        logger.info("[autoapply_db] user %s upgraded to plan %s", user_id, plan)
    except Exception as exc:
        logger.exception("[autoapply_db] update_user_plan error: %s", exc)
        raise


# ── Campaign functions ────────────────────────────────────────────────────────

async def create_campaign(
    user_id: int,
    job_title: str,
    location: str,
    salary_min: int,
    experience: str,
    platforms: list,
    daily_limit: int,
    db_path: str = AUTOAPPLY_DB,
) -> int:
    """Create a new campaign. Returns campaign_id."""
    now = datetime.utcnow().isoformat()
    platforms_json = json.dumps(platforms, ensure_ascii=False)
    try:
        async with aiosqlite.connect(db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO campaigns
                    (user_id, job_title, location, salary_min, experience,
                     platforms, daily_limit, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
                """,
                (user_id, job_title, location, salary_min, experience,
                 platforms_json, daily_limit, now),
            )
            await db.commit()
            return cur.lastrowid
    except Exception as exc:
        logger.exception("[autoapply_db] create_campaign error: %s", exc)
        raise


async def get_campaigns_for_user(user_id: int, db_path: str = AUTOAPPLY_DB) -> list:
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM campaigns WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ) as cur:
                rows = await cur.fetchall()
                result = []
                for row in rows:
                    d = dict(row)
                    try:
                        d["platforms"] = json.loads(d["platforms"] or "[]")
                    except (json.JSONDecodeError, TypeError):
                        d["platforms"] = []
                    result.append(d)
                return result
    except Exception as exc:
        logger.exception("[autoapply_db] get_campaigns_for_user error: %s", exc)
        return []


async def get_active_campaigns(db_path: str = AUTOAPPLY_DB) -> list:
    """Return all active campaigns across all users."""
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM campaigns WHERE status = 'active' ORDER BY last_run ASC NULLS FIRST"
            ) as cur:
                rows = await cur.fetchall()
                result = []
                for row in rows:
                    d = dict(row)
                    try:
                        d["platforms"] = json.loads(d["platforms"] or "[]")
                    except (json.JSONDecodeError, TypeError):
                        d["platforms"] = []
                    result.append(d)
                return result
    except Exception as exc:
        logger.exception("[autoapply_db] get_active_campaigns error: %s", exc)
        return []


async def update_campaign_status(
    campaign_id: int, status: str, db_path: str = AUTOAPPLY_DB
) -> None:
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE campaigns SET status = ? WHERE id = ?",
                (status, campaign_id),
            )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] update_campaign_status error: %s", exc)


async def update_campaign_last_run(
    campaign_id: int, db_path: str = AUTOAPPLY_DB
) -> None:
    try:
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE campaigns SET last_run = ? WHERE id = ?",
                (now, campaign_id),
            )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] update_campaign_last_run error: %s", exc)


# ── Application functions ─────────────────────────────────────────────────────

async def log_application(
    campaign_id: int,
    user_id: int,
    platform: str,
    vacancy_id: str,
    vacancy_title: str,
    company_name: str,
    vacancy_url: str,
    resume_used: str,
    db_path: str = AUTOAPPLY_DB,
) -> int:
    """Log a sent application. Also increments counters. Returns app_id."""
    now = datetime.utcnow().isoformat()
    try:
        async with aiosqlite.connect(db_path) as db:
            cur = await db.execute(
                """
                INSERT INTO applications
                    (campaign_id, user_id, platform, vacancy_id, vacancy_title,
                     company_name, vacancy_url, resume_used, status, sent_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'sent', ?)
                """,
                (campaign_id, user_id, platform, vacancy_id, vacancy_title,
                 company_name, vacancy_url, resume_used, now),
            )
            app_id = cur.lastrowid

            # Increment counters
            await db.execute(
                """
                UPDATE autoapply_users
                SET applications_today  = applications_today  + 1,
                    applications_total  = applications_total  + 1
                WHERE id = ?
                """,
                (user_id,),
            )
            await db.execute(
                "UPDATE campaigns SET applications_sent = applications_sent + 1 WHERE id = ?",
                (campaign_id,),
            )
            await db.commit()
            return app_id
    except Exception as exc:
        logger.exception("[autoapply_db] log_application error: %s", exc)
        raise


async def update_application_status(
    app_id: int, status: str, db_path: str = AUTOAPPLY_DB
) -> None:
    try:
        now = datetime.utcnow().isoformat()
        response_at = now if status in ("responded", "interview", "rejected") else None
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE applications SET status = ?, response_at = ? WHERE id = ?",
                (status, response_at, app_id),
            )
            if status == "responded":
                # Fetch user_id for this application to update counter
                async with db.execute(
                    "SELECT user_id, campaign_id FROM applications WHERE id = ?", (app_id,)
                ) as cur:
                    row = await cur.fetchone()
                    if row:
                        u_id, c_id = row
                        await db.execute(
                            "UPDATE autoapply_users SET responses_received = responses_received + 1 WHERE id = ?",
                            (u_id,),
                        )
                        await db.execute(
                            "UPDATE campaigns SET responses = responses + 1 WHERE id = ?",
                            (c_id,),
                        )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] update_application_status error: %s", exc)


async def get_applications_for_user(
    user_id: int,
    page: int = 1,
    per_page: int = 20,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    db_path: str = AUTOAPPLY_DB,
) -> dict:
    """Return paginated applications for a user."""
    try:
        offset = (page - 1) * per_page
        where_clauses = ["user_id = ?"]
        params: list = [user_id]

        if platform:
            where_clauses.append("platform = ?")
            params.append(platform)
        if status:
            where_clauses.append("status = ?")
            params.append(status)

        where_sql = " AND ".join(where_clauses)

        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                f"SELECT COUNT(*) FROM applications WHERE {where_sql}", params
            ) as cur:
                total_row = await cur.fetchone()
                total = total_row[0] if total_row else 0

            query_params = params + [per_page, offset]
            async with db.execute(
                f"""
                SELECT * FROM applications
                WHERE {where_sql}
                ORDER BY sent_at DESC
                LIMIT ? OFFSET ?
                """,
                query_params,
            ) as cur:
                rows = await cur.fetchall()
                items = [dict(r) for r in rows]

        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": max(1, (total + per_page - 1) // per_page),
        }
    except Exception as exc:
        logger.exception("[autoapply_db] get_applications_for_user error: %s", exc)
        return {"items": [], "total": 0, "page": page, "per_page": per_page, "pages": 1}


async def get_dashboard_stats(user_id: int, db_path: str = AUTOAPPLY_DB) -> dict:
    """Return aggregated dashboard stats for a user."""
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                "SELECT * FROM autoapply_users WHERE id = ?", (user_id,)
            ) as cur:
                user_row = await cur.fetchone()
            if not user_row:
                return {}
            user = dict(user_row)

            async with db.execute(
                "SELECT COUNT(*) FROM campaigns WHERE user_id = ? AND status = 'active'",
                (user_id,),
            ) as cur:
                active_campaigns_row = await cur.fetchone()
                active_campaigns = active_campaigns_row[0] if active_campaigns_row else 0

            async with db.execute(
                "SELECT COUNT(*) FROM campaigns WHERE user_id = ?", (user_id,)
            ) as cur:
                total_campaigns_row = await cur.fetchone()
                total_campaigns = total_campaigns_row[0] if total_campaigns_row else 0

            # Applications by platform
            async with db.execute(
                """
                SELECT platform, COUNT(*) as cnt
                FROM applications WHERE user_id = ?
                GROUP BY platform
                """,
                (user_id,),
            ) as cur:
                rows = await cur.fetchall()
                by_platform = {r["platform"]: r["cnt"] for r in rows}

            # Applications by status
            async with db.execute(
                """
                SELECT status, COUNT(*) as cnt
                FROM applications WHERE user_id = ?
                GROUP BY status
                """,
                (user_id,),
            ) as cur:
                rows = await cur.fetchall()
                by_status = {r["status"]: r["cnt"] for r in rows}

        plan_info = PLANS.get(user["plan"], PLANS["free"])
        response_rate = 0.0
        if user["applications_total"] > 0:
            response_rate = round(
                user["responses_received"] / user["applications_total"] * 100, 1
            )

        return {
            "user_id": user_id,
            "plan": user["plan"],
            "plan_label": plan_info["label"],
            "daily_limit": user["daily_limit"],
            "applications_today": user["applications_today"],
            "applications_total": user["applications_total"],
            "responses_received": user["responses_received"],
            "response_rate": response_rate,
            "active_campaigns": active_campaigns,
            "total_campaigns": total_campaigns,
            "by_platform": by_platform,
            "by_status": by_status,
            "hh_connected": bool(user.get("hh_token")),
            "resume_loaded": bool(user.get("resume_text")),
        }
    except Exception as exc:
        logger.exception("[autoapply_db] get_dashboard_stats error: %s", exc)
        return {}


async def is_vacancy_applied(
    vacancy_id: str, user_id: int, db_path: str = AUTOAPPLY_DB
) -> bool:
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT id FROM applications WHERE vacancy_id = ? AND user_id = ?",
                (vacancy_id, user_id),
            ) as cur:
                row = await cur.fetchone()
                return row is not None
    except Exception as exc:
        logger.exception("[autoapply_db] is_vacancy_applied error: %s", exc)
        return False


# ── Vacancy cache ─────────────────────────────────────────────────────────────

async def cache_vacancy(
    platform: str,
    vacancy_id: str,
    title: str,
    company: str,
    location: str,
    salary: str,
    description: str,
    url: str,
    db_path: str = AUTOAPPLY_DB,
) -> None:
    now = datetime.utcnow().isoformat()
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT INTO vacancies_cache
                    (platform, vacancy_id, title, company, location,
                     salary, description, url, fetched_at, applied)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(vacancy_id) DO UPDATE SET
                    fetched_at  = excluded.fetched_at,
                    description = excluded.description,
                    salary      = excluded.salary
                """,
                (platform, vacancy_id, title, company, location,
                 salary, description, url, now),
            )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] cache_vacancy error: %s", exc)


async def get_cached_vacancies(
    platform: str,
    job_title: str,
    location: str,
    max_age_hours: int = 1,
    db_path: str = AUTOAPPLY_DB,
) -> list:
    """Return cached vacancies for given platform/title/location, filtered by freshness."""
    try:
        cutoff = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM vacancies_cache
                WHERE platform = ?
                  AND title LIKE ?
                  AND (location LIKE ? OR location IS NULL OR location = '')
                  AND fetched_at > ?
                ORDER BY fetched_at DESC
                """,
                (platform, f"%{job_title}%", f"%{location}%", cutoff),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
    except Exception as exc:
        logger.exception("[autoapply_db] get_cached_vacancies error: %s", exc)
        return []


# ── Email token functions ─────────────────────────────────────────────────────

import secrets as _secrets

async def create_email_token(user_id: int, kind: str, ttl_hours: int = 24, db_path: str = AUTOAPPLY_DB) -> str:
    """Create a one-time token for email verification or password reset. Returns token string."""
    token = _secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(hours=ttl_hours)).isoformat()
    try:
        async with aiosqlite.connect(db_path) as db:
            # Invalidate previous unused tokens of same kind for this user
            await db.execute(
                "UPDATE email_tokens SET used = 1 WHERE user_id = ? AND kind = ? AND used = 0",
                (user_id, kind),
            )
            await db.execute(
                "INSERT INTO email_tokens (user_id, token, kind, expires_at, used) VALUES (?, ?, ?, ?, 0)",
                (user_id, token, kind, expires_at),
            )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] create_email_token error: %s", exc)
        raise
    return token


async def consume_email_token(token: str, kind: str, db_path: str = AUTOAPPLY_DB) -> Optional[int]:
    """Validate and consume a token. Returns user_id if valid, None otherwise."""
    try:
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM email_tokens WHERE token = ? AND kind = ? AND used = 0 AND expires_at > ?",
                (token, kind, now),
            ) as cur:
                row = await cur.fetchone()
            if not row:
                return None
            user_id = row["user_id"]
            await db.execute("UPDATE email_tokens SET used = 1 WHERE token = ?", (token,))
            await db.commit()
            return user_id
    except Exception as exc:
        logger.exception("[autoapply_db] consume_email_token error: %s", exc)
        return None


async def mark_user_verified(user_id: int, db_path: str = AUTOAPPLY_DB) -> None:
    """Set is_verified = 1 for a user."""
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute("UPDATE autoapply_users SET is_verified = 1 WHERE id = ?", (user_id,))
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] mark_user_verified error: %s", exc)


async def update_user_password(user_id: int, password_hash: str, db_path: str = AUTOAPPLY_DB) -> None:
    """Update password hash for a user."""
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE autoapply_users SET password_hash = ? WHERE id = ?",
                (password_hash, user_id),
            )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] update_user_password error: %s", exc)
        raise


# ── Daily reset ───────────────────────────────────────────────────────────────

async def reset_daily_counts(db_path: str = AUTOAPPLY_DB) -> None:
    """Reset applications_today to 0 for all users. Call at midnight."""
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE autoapply_users SET applications_today = 0"
            )
            await db.commit()
        logger.info("[autoapply_db] reset_daily_counts: all users reset")
    except Exception as exc:
        logger.exception("[autoapply_db] reset_daily_counts error: %s", exc)
