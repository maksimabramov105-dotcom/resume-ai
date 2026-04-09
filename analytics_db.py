"""
analytics_db.py — Analytics database layer for РезюмеАИ bot.

Connects to the EXISTING SQLite database at DB_PATH.
ONLY creates NEW tables — never touches or alters existing ones.
All functions are async using aiosqlite.

Existing tables (READ ONLY, never modified):
  - users           : telegram_id, username, full_name, referral_code, referred_by,
                      credits_*, total_resumes_generated, total_assistant_messages,
                      total_spent_rub, created_at, last_active
  - payments        : id, telegram_id, amount_rub, package, status, payment_id, created_at
                      NOTE: no payment_method column — use analytics_tracker.py for per-method revenue
  - generation_logs : id, telegram_id, type, input_text, result_text, tokens_used, cost_usd, created_at
                      type values: "resume", "cover_letter", "interview", "analysis", "assistant"
  - assistant_conversations : id, telegram_id, role, content, tokens_used, created_at
"""

import aiosqlite
import logging
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

# Path to the SQLite file on VPS
DB_PATH = "/opt/resumeaibot/bot.db"

# ── DDL for new analytics tables ──────────────────────────────────────────────

_CREATE_DAILY_STATS = """
CREATE TABLE IF NOT EXISTS daily_stats (
    date                 TEXT PRIMARY KEY,
    new_users            INTEGER DEFAULT 0,
    active_users         INTEGER DEFAULT 0,
    new_paid_users       INTEGER DEFAULT 0,
    total_paid_users     INTEGER DEFAULT 0,
    revenue_crypto       REAL    DEFAULT 0,
    revenue_card         REAL    DEFAULT 0,
    revenue_revolut      REAL    DEFAULT 0,
    resumes_generated    INTEGER DEFAULT 0,
    letters_generated    INTEGER DEFAULT 0,
    interviews_done      INTEGER DEFAULT 0,
    vacancy_analyses     INTEGER DEFAULT 0,
    ai_messages          INTEGER DEFAULT 0,
    referrals_made       INTEGER DEFAULT 0,
    outreach_conversions INTEGER DEFAULT 0
)
"""

_CREATE_JOIN_SOURCES = """
CREATE TABLE IF NOT EXISTS join_sources (
    user_id     INTEGER PRIMARY KEY,
    source      TEXT,
    recorded_at TEXT
)
"""

_CREATE_OUTREACH_LOG = """
CREATE TABLE IF NOT EXISTS outreach_log (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    date                  TEXT,
    messages_sent         INTEGER DEFAULT 0,
    estimated_conversions INTEGER DEFAULT 0
)
"""

_CREATE_CONTENT_LOG = """
CREATE TABLE IF NOT EXISTS content_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    date             TEXT,
    platform         TEXT,
    post_title       TEXT,
    post_url         TEXT,
    estimated_clicks INTEGER DEFAULT 0
)
"""


# ── Table initialisation ──────────────────────────────────────────────────────

async def init_analytics_db(db_path: str = DB_PATH) -> None:
    """
    Creates all four analytics tables if they don't already exist.
    Safe to call on every bot startup — uses CREATE TABLE IF NOT EXISTS.
    NEVER modifies existing tables.
    """
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_CREATE_DAILY_STATS)
        await db.execute(_CREATE_JOIN_SOURCES)
        await db.execute(_CREATE_OUTREACH_LOG)
        await db.execute(_CREATE_CONTENT_LOG)
        await db.commit()
    logger.info("Analytics DB tables initialised at %s", db_path)


# ── Core computation ──────────────────────────────────────────────────────────

async def compute_daily_stats(date_str: str, db_path: str = DB_PATH) -> None:
    """
    Reads from existing tables to compute stats for date_str ('YYYY-MM-DD'),
    then upserts the result into daily_stats.

    Revenue columns (revenue_crypto / revenue_card / revenue_revolut) are NOT
    overwritten here because they are written in real-time by analytics_tracker
    .track_payment(). We only update the columns that can be derived from the
    existing schema.
    """
    async with aiosqlite.connect(db_path) as db:

        # new_users: registered on this date
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(created_at) = ?", (date_str,)
        ) as cur:
            new_users = (await cur.fetchone())[0]

        # active_users: at least one generation_log entry on this date
        async with db.execute(
            "SELECT COUNT(DISTINCT telegram_id) FROM generation_logs WHERE DATE(created_at) = ?",
            (date_str,)
        ) as cur:
            active_users = (await cur.fetchone())[0]

        # new_paid_users: distinct users with a 'succeeded' payment created today
        async with db.execute(
            """SELECT COUNT(DISTINCT telegram_id) FROM payments
               WHERE status = 'succeeded' AND DATE(created_at) = ?""",
            (date_str,)
        ) as cur:
            new_paid_users = (await cur.fetchone())[0]

        # total_paid_users: all time
        async with db.execute(
            "SELECT COUNT(DISTINCT telegram_id) FROM payments WHERE status = 'succeeded'"
        ) as cur:
            total_paid_users = (await cur.fetchone())[0]

        # feature usage: generation_logs.type breakdown
        # Known values: "resume", "cover_letter", "interview", "analysis", "assistant"
        async with db.execute(
            "SELECT type, COUNT(*) FROM generation_logs WHERE DATE(created_at) = ? GROUP BY type",
            (date_str,)
        ) as cur:
            type_rows = await cur.fetchall()
        usage = {r[0]: r[1] for r in type_rows}

        # referrals made: new users who joined via a referral on this date
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL AND DATE(created_at) = ?",
            (date_str,)
        ) as cur:
            referrals = (await cur.fetchone())[0]

        # Upsert: create row if it doesn't exist, then update non-revenue columns
        await db.execute(
            "INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (date_str,)
        )
        await db.execute(
            """UPDATE daily_stats SET
                new_users         = ?,
                active_users      = ?,
                new_paid_users    = ?,
                total_paid_users  = ?,
                resumes_generated = ?,
                letters_generated = ?,
                interviews_done   = ?,
                vacancy_analyses  = ?,
                ai_messages       = ?,
                referrals_made    = ?
               WHERE date = ?""",
            (
                new_users, active_users, new_paid_users, total_paid_users,
                usage.get("resume", 0),
                usage.get("cover_letter", 0),
                usage.get("interview", 0),
                usage.get("analysis", 0),
                usage.get("assistant", 0),
                referrals,
                date_str,
            )
        )
        await db.commit()


# ── Summary / reporting queries ───────────────────────────────────────────────

async def get_full_summary(db_path: str = DB_PATH) -> dict:
    """
    Returns a single dict with all key metrics needed for the daily report
    and dashboard overview. Defaults every value to 0 — never raises.
    """
    today = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    result: dict = {}

    async with aiosqlite.connect(db_path) as db:

        # ── User counts ───────────────────────────────────────────────────────
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            result["total_users"] = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(created_at) = ?", (today,)
        ) as cur:
            result["new_users_today"] = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(DISTINCT telegram_id) FROM payments WHERE status = 'succeeded'"
        ) as cur:
            result["total_paid_users"] = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(DISTINCT telegram_id) FROM payments WHERE status='succeeded' AND DATE(created_at)=?",
            (today,)
        ) as cur:
            result["new_paid_today"] = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(DISTINCT telegram_id) FROM generation_logs WHERE DATE(created_at) = ?",
            (today,)
        ) as cur:
            result["active_today"] = (await cur.fetchone())[0]

        # Users inactive for 7+ days (rough churn proxy)
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(last_active) < ?", (week_ago,)
        ) as cur:
            result["inactive_7d"] = (await cur.fetchone())[0]

        # ── Revenue ───────────────────────────────────────────────────────────
        async with db.execute(
            "SELECT COALESCE(SUM(amount_rub), 0) FROM payments WHERE status = 'succeeded'"
        ) as cur:
            result["total_revenue_rub"] = (await cur.fetchone())[0]

        # Today's revenue by method (tracked in real-time by analytics_tracker)
        async with db.execute(
            """SELECT COALESCE(revenue_crypto,0),
                      COALESCE(revenue_card,0),
                      COALESCE(revenue_revolut,0)
               FROM daily_stats WHERE date = ?""",
            (today,)
        ) as cur:
            row = await cur.fetchone()
        if row:
            result["revenue_crypto_today"]  = row[0]
            result["revenue_card_today"]    = row[1]
            result["revenue_revolut_today"] = row[2]
        else:
            result["revenue_crypto_today"]  = 0
            result["revenue_card_today"]    = 0
            result["revenue_revolut_today"] = 0
        result["revenue_today_rub"] = (
            result["revenue_crypto_today"]
            + result["revenue_card_today"]
            + result["revenue_revolut_today"]
        )

        # ── Feature usage today ───────────────────────────────────────────────
        async with db.execute(
            "SELECT type, COUNT(*) FROM generation_logs WHERE DATE(created_at) = ? GROUP BY type",
            (today,)
        ) as cur:
            rows = await cur.fetchall()
        usage = {r[0]: r[1] for r in rows}
        result["resumes_today"]      = usage.get("resume", 0)
        result["letters_today"]      = usage.get("cover_letter", 0)
        result["interviews_today"]   = usage.get("interview", 0)
        result["analyses_today"]     = usage.get("analysis", 0)
        result["ai_messages_today"]  = usage.get("assistant", 0)

        # ── Referrals today ───────────────────────────────────────────────────
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL AND DATE(created_at) = ?",
            (today,)
        ) as cur:
            result["referrals_today"] = (await cur.fetchone())[0]

        # ── Top referrer (single user, for daily report headline) ─────────────
        async with db.execute(
            """SELECT u.username, u.telegram_id, COUNT(*) AS cnt
               FROM users r
               JOIN users u ON u.telegram_id = r.referred_by
               WHERE r.referred_by IS NOT NULL
               GROUP BY r.referred_by
               ORDER BY cnt DESC LIMIT 1"""
        ) as cur:
            row = await cur.fetchone()
        result["top_referrer_username"] = row[0] if row else None
        result["top_referrer_id"]       = row[1] if row else None
        result["top_referrer_count"]    = row[2] if row else 0

        # ── Outreach conversions today (from outreach_log) ────────────────────
        async with db.execute(
            "SELECT COALESCE(SUM(estimated_conversions),0) FROM outreach_log WHERE date=?",
            (today,)
        ) as cur:
            result["outreach_conversions_today"] = (await cur.fetchone())[0]

        # ── 7-day average daily paid growth (used for ETA calc) ───────────────
        async with db.execute(
            "SELECT AVG(new_paid_users) FROM daily_stats WHERE date >= ? AND date < ?",
            (week_ago, today)
        ) as cur:
            avg = (await cur.fetchone())[0]
        result["avg_daily_paid_growth"] = avg or 0.0

    # ── Derived ───────────────────────────────────────────────────────────────
    total = result["total_users"]
    paid  = result["total_paid_users"]
    result["conversion_rate"] = round(paid / total * 100, 1) if total > 0 else 0.0

    return result


async def get_top_referrers(n: int = 10, db_path: str = DB_PATH) -> list:
    """
    Returns top N referrers as a list of dicts.
    Joins users table twice: referred users and the referrer.
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """SELECT u.telegram_id, u.username, u.full_name, COUNT(*) AS cnt
               FROM users r
               JOIN users u ON u.telegram_id = r.referred_by
               WHERE r.referred_by IS NOT NULL
               GROUP BY r.referred_by
               ORDER BY cnt DESC
               LIMIT ?""",
            (n,)
        ) as cur:
            rows = await cur.fetchall()
    return [
        {"telegram_id": r[0], "username": r[1], "full_name": r[2], "referred_count": r[3]}
        for r in rows
    ]


async def get_revenue_by_plan(db_path: str = DB_PATH) -> list:
    """
    Groups succeeded payments by package name.
    Returns list of {package, count, total_rub}.
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """SELECT package, COUNT(*) AS cnt, COALESCE(SUM(amount_rub),0) AS total
               FROM payments WHERE status = 'succeeded'
               GROUP BY package ORDER BY total DESC"""
        ) as cur:
            rows = await cur.fetchall()
    return [{"package": r[0], "count": r[1], "total_rub": r[2]} for r in rows]


async def get_daily_stats_range(days: int = 30, db_path: str = DB_PATH) -> list:
    """
    Returns the last N days of daily_stats as a list of dicts, sorted by date ASC.
    Only returns rows that actually exist in the table.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    cols = [
        "date", "new_users", "active_users", "new_paid_users", "total_paid_users",
        "revenue_crypto", "revenue_card", "revenue_revolut",
        "resumes_generated", "letters_generated", "interviews_done",
        "vacancy_analyses", "ai_messages", "referrals_made", "outreach_conversions",
    ]
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"SELECT {', '.join(cols)} FROM daily_stats WHERE date >= ? ORDER BY date ASC",
            (cutoff,)
        ) as cur:
            rows = await cur.fetchall()
    return [dict(zip(cols, r)) for r in rows]


async def log_outreach(
    date_str: str, sent: int, conversions: int, db_path: str = DB_PATH
) -> None:
    """Appends one row to outreach_log."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO outreach_log (date, messages_sent, estimated_conversions) VALUES (?,?,?)",
            (date_str, sent, conversions)
        )
        await db.commit()


async def log_content(
    date_str: str, platform: str, title: str, url: str,
    clicks: int = 0, db_path: str = DB_PATH
) -> None:
    """Appends one row to content_log."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO content_log (date, platform, post_title, post_url, estimated_clicks) VALUES (?,?,?,?,?)",
            (date_str, platform, title, url, clicks)
        )
        await db.commit()
