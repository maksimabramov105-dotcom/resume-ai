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

_MIGRATE_CONSENT_AT = """
ALTER TABLE autoapply_users ADD COLUMN consent_at TEXT
"""

_MIGRATE_STRIPE_CUSTOMER_ID = """
ALTER TABLE autoapply_users ADD COLUMN stripe_customer_id TEXT
"""

_MIGRATE_COMPANY_COUNTRY = """
ALTER TABLE applications ADD COLUMN company_country TEXT
"""

_CREATE_EMAIL_DRIP = """
CREATE TABLE IF NOT EXISTS email_drip (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    step INTEGER NOT NULL DEFAULT 0,
    next_send_at TIMESTAMP,
    completed INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES autoapply_users(id)
)
"""

_CREATE_TESTIMONIALS = """
CREATE TABLE IF NOT EXISTS testimonials (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    name        TEXT    NOT NULL,
    text        TEXT    NOT NULL,
    rating      INTEGER NOT NULL DEFAULT 5,
    approved    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now'))
)
"""

_CREATE_WEB_GENERATIONS = """
CREATE TABLE IF NOT EXISTS web_generations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    type       TEXT NOT NULL,  -- 'resume', 'cover_letter', 'analysis', 'demo_analysis'
    created_at TEXT DEFAULT (datetime('now'))
)
"""

_CREATE_PAGE_VIEWS = """
CREATE TABLE IF NOT EXISTS page_views (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    page       TEXT,
    referrer   TEXT,
    ip_hash    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

_CREATE_RATE_LIMITS = """
CREATE TABLE IF NOT EXISTS rate_limits (
    key        TEXT PRIMARY KEY,
    last_hit   REAL NOT NULL
)
"""

# ── Indexes ───────────────────────────────────────────────────────────────────

_CREATE_INDEXES = [
    # Users — most-queried column (login, auth)
    "CREATE INDEX IF NOT EXISTS idx_users_email ON autoapply_users(email)",
    "CREATE INDEX IF NOT EXISTS idx_users_created_at ON autoapply_users(created_at)",
    # Campaigns — by owner, hot on dashboard
    "CREATE INDEX IF NOT EXISTS idx_campaigns_user_id ON campaigns(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status)",
    # Applications — by campaign and user for listing
    "CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_applications_campaign_id ON applications(campaign_id)",
    "CREATE INDEX IF NOT EXISTS idx_applications_sent_at ON applications(sent_at)",
    # Email tokens — by token (consumed on every email-verify / reset click)
    "CREATE INDEX IF NOT EXISTS idx_email_tokens_token ON email_tokens(token)",
    "CREATE INDEX IF NOT EXISTS idx_email_tokens_user_id ON email_tokens(user_id)",
    # Drip — scheduler polls this table every minute
    "CREATE INDEX IF NOT EXISTS idx_drip_user_id ON email_drip(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_drip_next_send ON email_drip(next_send_at) WHERE completed = 0",
    # Web generations — rolling-window aggregate queries
    "CREATE INDEX IF NOT EXISTS idx_web_gen_created_at ON web_generations(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_web_gen_user_id ON web_generations(user_id)",
    # Page views — daily/24h analytics queries
    "CREATE INDEX IF NOT EXISTS idx_page_views_created_at ON page_views(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_page_views_ip_hash ON page_views(ip_hash)",
    # Rate limits — keyed by "type:ip", cleaned up periodically
    "CREATE INDEX IF NOT EXISTS idx_rate_limits_last_hit ON rate_limits(last_hit)",
]

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
            await db.execute(_CREATE_EMAIL_DRIP)
            await db.execute(_CREATE_TESTIMONIALS)
            await db.execute(_CREATE_WEB_GENERATIONS)
            await db.execute(_CREATE_PAGE_VIEWS)
            await db.execute(_CREATE_RATE_LIMITS)
            # Indexes
            for _idx_sql in _CREATE_INDEXES:
                try:
                    await db.execute(_idx_sql)
                except Exception:
                    pass  # partial-index syntax not supported on older SQLite
            # Migrations — each wrapped individually so one failure doesn't block others
            for _migration in (
                _MIGRATE_IS_VERIFIED,
                _MIGRATE_CONSENT_AT,
                _MIGRATE_STRIPE_CUSTOMER_ID,
                _MIGRATE_COMPANY_COUNTRY,
            ):
                try:
                    await db.execute(_migration)
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
    company_country: Optional[str] = None,
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
                     company_name, vacancy_url, resume_used, status, sent_at,
                     company_country)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'sent', ?, ?)
                """,
                (campaign_id, user_id, platform, vacancy_id, vacancy_title,
                 company_name, vacancy_url, resume_used, now, company_country),
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


async def record_consent(user_id: int, db_path: str = AUTOAPPLY_DB) -> None:
    """Stamp consent_at = UTC now for a user (GDPR / ToS acceptance at campaign creation).
    Idempotent: only sets the timestamp the first time (when consent_at IS NULL).
    """
    now = datetime.utcnow().isoformat()
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE autoapply_users SET consent_at = ? WHERE id = ? AND consent_at IS NULL",
                (now, user_id),
            )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] record_consent error: %s", exc)


async def save_linkedin_credentials(
    user_id: int,
    email: str,
    password: str,
    db_path: str = AUTOAPPLY_DB,
) -> None:
    """Encrypt and persist LinkedIn credentials for a user.
    Uses Fernet encryption via crypto.py (falls back to plaintext if ENCRYPTION_KEY unset).
    """
    from autoapply.crypto import encrypt
    encrypted_pw = encrypt(password)
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE autoapply_users SET linkedin_email = ?, linkedin_password_enc = ? WHERE id = ?",
                (email, encrypted_pw, user_id),
            )
            await db.commit()
        logger.info(
            "[autoapply_db] linkedin credentials saved user_id=%s encrypted=%s",
            user_id,
            encrypted_pw != password,  # True when ENCRYPTION_KEY is set
        )
    except Exception as exc:
        logger.exception("[autoapply_db] save_linkedin_credentials error: %s", exc)
        raise


async def get_linkedin_credentials(
    user_id: int,
    db_path: str = AUTOAPPLY_DB,
) -> Optional[tuple]:
    """Return (email, plaintext_password) or None if LinkedIn is not connected.
    Decrypts linkedin_password_enc via crypto.py.
    """
    from autoapply.crypto import decrypt
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT linkedin_email, linkedin_password_enc FROM autoapply_users WHERE id = ?",
                (user_id,),
            ) as cur:
                row = await cur.fetchone()
        if not row or not row[0] or not row[1]:
            return None
        return row[0], decrypt(row[1])
    except Exception as exc:
        logger.exception("[autoapply_db] get_linkedin_credentials error: %s", exc)
        return None


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


# ── Email drip functions ──────────────────────────────────────────────────────

async def create_drip_sequence(user_id: int, db_path: str = AUTOAPPLY_DB) -> None:
    """Start email drip for a new user."""
    from datetime import timezone
    next_send = datetime.now(timezone.utc)  # Send first email immediately
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO email_drip (user_id, step, next_send_at) VALUES (?, 0, ?)",
                (user_id, next_send.isoformat())
            )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] create_drip_sequence error: %s", exc)


async def get_pending_drip_users(db_path: str = AUTOAPPLY_DB) -> list:
    """Get users whose next drip email is due."""
    from datetime import timezone
    now = datetime.now(timezone.utc).isoformat()
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT d.id, d.user_id, d.step, u.email
                FROM email_drip d
                JOIN autoapply_users u ON u.id = d.user_id
                WHERE d.completed = 0
                  AND d.next_send_at <= ?
                  AND u.is_verified = 1
                LIMIT 50
            """, (now,)) as cur:
                return [dict(r) for r in await cur.fetchall()]
    except Exception as exc:
        logger.exception("[autoapply_db] get_pending_drip_users error: %s", exc)
        return []


async def advance_drip_step(drip_id: int, next_send_at, completed: bool = False, db_path: str = AUTOAPPLY_DB) -> None:
    """Move to next drip step."""
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "UPDATE email_drip SET step = step + 1, next_send_at = ?, completed = ? WHERE id = ?",
                (next_send_at.isoformat() if next_send_at else None, 1 if completed else 0, drip_id)
            )
            await db.commit()
    except Exception as exc:
        logger.exception("[autoapply_db] advance_drip_step error: %s", exc)


async def log_web_generation(gen_type: str, user_id: int = None, db_path: str = AUTOAPPLY_DB) -> None:
    """Log a web app generation event (resume, cover_letter, analysis, demo_analysis)."""
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT INTO web_generations (user_id, type) VALUES (?, ?)",
                (user_id, gen_type)
            )
            await db.commit()
    except Exception as exc:
        logger.warning("[autoapply_db] log_web_generation error: %s", exc)


# ── Rate limiting ─────────────────────────────────────────────────────────────

import time as _rl_time

async def check_and_update_rate_limit(
    key: str, window_seconds: float, db_path: str = AUTOAPPLY_DB
) -> bool:
    """Return True (allowed) or False (blocked). Persists across restarts.
    `key` should be namespaced, e.g. 'demo:192.168.1.1'.
    """
    now = _rl_time.time()
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT last_hit FROM rate_limits WHERE key=?", (key,)
            ) as cur:
                row = await cur.fetchone()
            if row and (now - row[0]) < window_seconds:
                return False  # still within cooldown window
            await db.execute(
                "INSERT OR REPLACE INTO rate_limits (key, last_hit) VALUES (?, ?)",
                (key, now),
            )
            await db.commit()
        return True
    except Exception as exc:
        logger.warning("[rate_limit] DB error — allowing request: %s", exc)
        return True  # fail open so a DB hiccup doesn't block users


async def cleanup_rate_limits(older_than_seconds: float = 86400, db_path: str = AUTOAPPLY_DB) -> None:
    """Delete stale rate-limit rows (default: older than 24 h)."""
    cutoff = _rl_time.time() - older_than_seconds
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute("DELETE FROM rate_limits WHERE last_hit < ?", (cutoff,))
            await db.commit()
    except Exception as exc:
        logger.warning("[rate_limit] cleanup error: %s", exc)
