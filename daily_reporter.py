"""
daily_reporter.py — Sends daily and weekly analytics reports to the admin.

Covers BOTH products:
  - Telegram bot (@topbestworkerbot) stats from analytics_db / bot.db
  - AutoApply web service stats from autoapply.db

Does NOT create a new APScheduler instance.
Exports two async functions to be added as jobs to the EXISTING scheduler
in run.py. See INTEGRATION INSTRUCTIONS at the bottom of this file.
"""

import asyncio
import logging
import os
import sqlite3
from datetime import date, timedelta

# analytics_db is in the same directory (project root), added to sys.path by run.py
from analytics_db import get_full_summary, get_top_referrers, get_daily_stats_range, DB_PATH

AUTOAPPLY_DB = os.getenv("AUTOAPPLY_DB", "/opt/resumeaibot/autoapply.db")

logger = logging.getLogger(__name__)

ADMIN_CHAT_ID = 6246429438   # Your Telegram ID

# Russian weekday names (Monday = index 0)
_WEEKDAYS_RU = [
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье",
]


# ── Formatting helpers ────────────────────────────────────────────────────────

def _get_autoapply_stats() -> dict:
    """
    Reads today's AutoApply web service stats from autoapply.db.
    Uses sync sqlite3 (safe to call from async context — read-only, instant).
    Returns empty dict on any error so the daily report never crashes.
    """
    try:
        if not os.path.exists(AUTOAPPLY_DB):
            return {}
        con = sqlite3.connect(AUTOAPPLY_DB)
        con.row_factory = sqlite3.Row
        today = date.today().isoformat()

        # Total registered web users
        total_web = con.execute("SELECT COUNT(*) FROM autoapply_users").fetchone()[0]
        # New web users today (registered today)
        new_web_today = con.execute(
            "SELECT COUNT(*) FROM autoapply_users WHERE date(created_at) = ?", (today,)
        ).fetchone()[0]
        # Applications sent today across all users
        apps_today = con.execute(
            "SELECT COUNT(*) FROM applications WHERE date(sent_at) = ?", (today,)
        ).fetchone()[0]
        # Total applications ever
        apps_total = con.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        # Responses/interviews received today
        responses_today = con.execute(
            "SELECT COUNT(*) FROM applications WHERE status IN ('response','interview') AND date(response_at) = ?",
            (today,)
        ).fetchone()[0]
        # Active campaigns
        active_campaigns = con.execute(
            "SELECT COUNT(*) FROM campaigns WHERE status = 'active'"
        ).fetchone()[0]
        # Revenue from paid plan upgrades (users with paid plans)
        paid_web_users = con.execute(
            "SELECT COUNT(*) FROM autoapply_users WHERE plan != 'free'"
        ).fetchone()[0]
        # Bot→web transitions: users who have both telegram_id set and are web users
        bot_to_web = con.execute(
            "SELECT COUNT(*) FROM autoapply_users WHERE telegram_id IS NOT NULL"
        ).fetchone()[0]

        # Web generations (resume, cover letter, analysis) — from web_generations table
        web_resumes_today = 0
        web_letters_today = 0
        web_analyses_today = 0
        web_resumes_total = 0
        web_autoapply_today = 0
        try:
            web_resumes_today = con.execute(
                "SELECT COUNT(*) FROM web_generations WHERE type='resume' AND date(created_at)=?", (today,)
            ).fetchone()[0]
            web_letters_today = con.execute(
                "SELECT COUNT(*) FROM web_generations WHERE type='cover_letter' AND date(created_at)=?", (today,)
            ).fetchone()[0]
            web_analyses_today = con.execute(
                "SELECT COUNT(*) FROM web_generations WHERE type IN ('analysis','demo_analysis') AND date(created_at)=?", (today,)
            ).fetchone()[0]
            web_resumes_total = con.execute(
                "SELECT COUNT(*) FROM web_generations WHERE type='resume'"
            ).fetchone()[0]
            web_autoapply_today = con.execute(
                "SELECT COUNT(*) FROM web_generations WHERE type='autoapply' AND date(created_at)=?", (today,)
            ).fetchone()[0]
        except Exception:
            pass  # table may not exist on older installs

        con.close()
        return {
            "total_web_users":      total_web,
            "new_web_today":        new_web_today,
            "apps_today":           apps_today,
            "apps_total":           apps_total,
            "responses_today":      responses_today,
            "active_campaigns":     active_campaigns,
            "paid_web_users":       paid_web_users,
            "bot_to_web":           bot_to_web,
            "web_resumes_today":    web_resumes_today,
            "web_letters_today":    web_letters_today,
            "web_analyses_today":   web_analyses_today,
            "web_resumes_total":    web_resumes_total,
            "web_autoapply_today":  web_autoapply_today,
        }
    except Exception as e:
        logging.getLogger(__name__).warning("_get_autoapply_stats error: %s", e)
        return {}


def _progress_bar(current: int, goal: int = 1000, width: int = 20) -> str:
    """
    Returns an emoji-filled progress bar.
    Example at 35%: [███████░░░░░░░░░░░░░]
    """
    if goal <= 0:
        return "[" + "░" * width + "]"
    filled = min(int(current / goal * width), width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def _eta_string(current: int, avg_daily: float, goal: int = 1000) -> str:
    """
    Calculates when the goal will be reached at the current daily growth rate.
    Returns a date string like "15.06.2025" or a fallback message.
    """
    if avg_daily <= 0:
        return "темп пока не определён"
    remaining = goal - current
    if remaining <= 0:
        return "🎉 цель достигнута!"
    days_left = int(remaining / avg_daily)
    eta = date.today() + timedelta(days=days_left)
    return eta.strftime("%d.%m.%Y")


# ── Daily report ──────────────────────────────────────────────────────────────

async def send_daily_report(
    bot,
    admin_chat_id: int = ADMIN_CHAT_ID,
    db_path: str = DB_PATH,
) -> None:
    """
    Fetches all analytics and sends a formatted daily report to admin_chat_id.
    Completely safe — catches all exceptions, never crashes the scheduler.
    """
    try:
        summary  = await get_full_summary(db_path)
        top_refs = await get_top_referrers(n=1, db_path=db_path)
        web_stats = _get_autoapply_stats()
    except Exception as e:
        logger.error("Daily report: failed to fetch analytics: %s", e)
        try:
            await bot.send_message(admin_chat_id, "⚠️ Дневной отчёт: ошибка чтения базы данных.")
        except Exception:
            pass
        return

    # ── Date header ───────────────────────────────────────────────────────────
    today      = date.today()
    weekday_ru = _WEEKDAYS_RU[today.weekday()]
    date_str   = today.strftime("%d.%m.%Y")

    # ── Revenue ───────────────────────────────────────────────────────────────
    rev_crypto  = summary.get("revenue_crypto_today", 0)
    rev_card    = summary.get("revenue_card_today", 0)
    rev_revolut = summary.get("revenue_revolut_today", 0)
    rev_total   = rev_crypto + rev_card + rev_revolut

    # ── Goal tracker ──────────────────────────────────────────────────────────
    paid_total = summary.get("total_paid_users", 0)
    goal       = 1000
    bar        = _progress_bar(paid_total, goal)
    pct        = round(paid_total / goal * 100, 1) if goal > 0 else 0
    remaining  = max(0, goal - paid_total)
    avg_daily  = summary.get("avg_daily_paid_growth", 0.0)
    eta        = _eta_string(paid_total, avg_daily, goal)

    # ── Top referrer ──────────────────────────────────────────────────────────
    if top_refs:
        r = top_refs[0]
        display = f"@{r['username']}" if r.get("username") else f"id{r['telegram_id']}"
        top_ref_str = f"{display} ({r['referred_count']} чел.)"
    else:
        top_ref_str = "нет данных"

    text = (
        f"📊 <b>РезюмеАИ — Дневной отчёт</b>\n"
        f"📅 {weekday_ru}, {date_str}\n"
        f"─────────────────────────────────────\n\n"

        f"👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
        f"┌ Новых сегодня: +{summary.get('new_users_today', 0)}\n"
        f"├ Всего: {summary.get('total_users', 0)}\n"
        f"├ Активных сегодня: {summary.get('active_today', 0)}\n"
        f"└ Отток (неактивны 7д): {summary.get('inactive_7d', 0)}\n\n"

        f"💰 <b>ВЫРУЧКА СЕГОДНЯ</b>\n"
        f"┌ Крипто: {rev_crypto:.0f}₽\n"
        f"├ Карта: {rev_card:.0f}₽\n"
        f"├ Revolut: {rev_revolut:.0f}₽\n"
        f"└ Итого: {rev_total:.0f}₽\n\n"

        f"📈 <b>КОНВЕРСИЯ</b>\n"
        f"┌ Free → Paid (всего): {summary.get('conversion_rate', 0):.1f}%\n"
        f"└ Новых платных сегодня: +{summary.get('new_paid_today', 0)} "
        f"(Всего: {paid_total})\n\n"

        f"🤖 <b>ИСПОЛЬЗОВАНИЕ</b>\n"
        f"┌ Резюме создано: {summary.get('resumes_today', 0)}\n"
        f"├ Писем создано: {summary.get('letters_today', 0)}\n"
        f"├ Собеседований: {summary.get('interviews_today', 0)}\n"
        f"├ Анализов вакансий: {summary.get('analyses_today', 0)}\n"
        f"└ AI-сообщений: {summary.get('ai_messages_today', 0)}\n\n"

        f"🔗 <b>РЕФЕРАЛЫ</b>\n"
        f"┌ Новых приглашений: {summary.get('referrals_today', 0)}\n"
        f"└ Топ реферер: {top_ref_str}\n\n"

        f"📣 <b>АУТРИЧ</b>\n"
        f"└ Конверсий сегодня: {summary.get('outreach_conversions_today', 0)}\n\n"
    )

    # ── AutoApply web service section (if DB available) ───────────────────────
    if web_stats:
        text += (
            f"🌐 <b>АвтоОтклик (веб-сервис)</b>\n"
            f"┌ Новых пользователей сайта: +{web_stats.get('new_web_today', 0)}\n"
            f"├ Всего на сайте: {web_stats.get('total_web_users', 0)} "
            f"(платных: {web_stats.get('paid_web_users', 0)})\n"
            f"├ Резюме создано на сайте: {web_stats.get('web_resumes_today', 0)} "
            f"(всего: {web_stats.get('web_resumes_total', 0)})\n"
            f"├ АвтоОтклик настроен сегодня: {web_stats.get('web_autoapply_today', 0)}\n"
            f"├ Писем создано на сайте: {web_stats.get('web_letters_today', 0)}\n"
            f"├ Анализов вакансий на сайте: {web_stats.get('web_analyses_today', 0)}\n"
            f"├ Заявок отправлено: {web_stats.get('apps_today', 0)} (всего: {web_stats.get('apps_total', 0)})\n"
            f"├ Ответов/собеседований: {web_stats.get('responses_today', 0)}\n"
            f"├ Активных кампаний: {web_stats.get('active_campaigns', 0)}\n"
            f"└ Бот→сайт (telegram linked): {web_stats.get('bot_to_web', 0)}\n\n"
        )

    text += (
        f"🎯 <b>ЦЕЛЬ: 1000 платных</b>\n"
        f"{bar} {pct:.1f}%\n"
        f"{paid_total} / {goal} — осталось {remaining}\n"
        f"При текущем темпе (+{avg_daily:.1f}/день): цель ~{eta}\n"
        f"─────────────────────────────────────"
    )

    try:
        await bot.send_message(admin_chat_id, text, parse_mode="HTML")
        logger.info("Daily report sent to admin %s", admin_chat_id)
    except Exception as e:
        logger.error("Daily report: failed to send message: %s", e)


# ── Weekly summary ────────────────────────────────────────────────────────────

async def send_weekly_summary(
    bot,
    admin_chat_id: int = ADMIN_CHAT_ID,
    db_path: str = DB_PATH,
) -> None:
    """
    Sends a 7-day summary: totals, best/worst day, revenue, goal progress.
    Designed to run right after the weekly digest job (Mon 10:05 MSK).
    """
    try:
        rows    = await get_daily_stats_range(days=7, db_path=db_path)
        summary = await get_full_summary(db_path)
    except Exception as e:
        logger.error("Weekly summary: failed to fetch data: %s", e)
        return

    today_str     = date.today().strftime("%d.%m.%Y")
    week_start    = (date.today() - timedelta(days=6)).strftime("%d.%m.%Y")

    if not rows:
        # Not enough data yet — send a minimal message
        await bot.send_message(
            admin_chat_id,
            f"📊 <b>РезюмеАИ — Недельный отчёт</b>\n"
            f"📅 {week_start} — {today_str}\n\n"
            f"Данных пока недостаточно. Отчёт будет полным на следующей неделе.",
            parse_mode="HTML",
        )
        return

    # ── Weekly aggregates ─────────────────────────────────────────────────────
    total_new_users  = sum(r["new_users"] for r in rows)
    total_new_paid   = sum(r["new_paid_users"] for r in rows)
    total_revenue    = sum(
        r["revenue_crypto"] + r["revenue_card"] + r["revenue_revolut"]
        for r in rows
    )
    total_gens = sum(
        r["resumes_generated"] + r["letters_generated"] + r["interviews_done"]
        + r["vacancy_analyses"] + r["ai_messages"]
        for r in rows
    )
    total_referrals = sum(r["referrals_made"] for r in rows)

    best  = max(rows, key=lambda r: r["new_users"])
    worst = min(rows, key=lambda r: r["new_users"])

    paid_total = summary.get("total_paid_users", 0)
    bar = _progress_bar(paid_total)
    pct = round(paid_total / 1000 * 100, 1)

    text = (
        f"📊 <b>РезюмеАИ — Недельный отчёт</b>\n"
        f"📅 {week_start} — {today_str}\n"
        f"─────────────────────────────────────\n\n"

        f"👥 <b>ПОЛЬЗОВАТЕЛИ</b>\n"
        f"┌ Новых за неделю: +{total_new_users}\n"
        f"├ Новых платных за неделю: +{total_new_paid}\n"
        f"└ Всего в базе: {summary.get('total_users', 0)}\n\n"

        f"💰 <b>ВЫРУЧКА ЗА НЕДЕЛЮ</b>\n"
        f"└ Итого: {total_revenue:.0f}₽\n\n"

        f"🤖 <b>ГЕНЕРАЦИЙ ЗА НЕДЕЛЮ</b>\n"
        f"└ Всего: {total_gens}\n\n"

        f"🔗 <b>РЕФЕРАЛОВ ЗА НЕДЕЛЮ</b>\n"
        f"└ {total_referrals}\n\n"

        f"📅 <b>ЛУЧШИЙ ДЕНЬ</b>\n"
        f"└ {best['date']}: +{best['new_users']} новых пользователей\n\n"

        f"📅 <b>ХУДШИЙ ДЕНЬ</b>\n"
        f"└ {worst['date']}: +{worst['new_users']} новых пользователей\n\n"

        f"🎯 <b>ЦЕЛЬ: 1000 платных</b>\n"
        f"{bar} {pct:.1f}%\n"
        f"{paid_total} / 1000 — конверсия {summary.get('conversion_rate', 0):.1f}%\n"
        f"─────────────────────────────────────"
    )

    try:
        await bot.send_message(admin_chat_id, text, parse_mode="HTML")
        logger.info("Weekly summary sent to admin %s", admin_chat_id)
    except Exception as e:
        logger.error("Weekly summary: failed to send message: %s", e)


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION INSTRUCTIONS
# Add these jobs to the EXISTING APScheduler in run.py
# (inside run_bot(), after the existing weekly digest job)
# ══════════════════════════════════════════════════════════════════════════════
#
# Step 1 — Add imports at the top of run.py:
#
#   import sys, os
#   ROOT = os.path.dirname(os.path.abspath(__file__))
#   if ROOT not in sys.path:
#       sys.path.insert(0, ROOT)
#   from daily_reporter import send_daily_report, send_weekly_summary, ADMIN_CHAT_ID
#   from analytics_db import DB_PATH
#
# Step 2 — Add jobs inside run_bot(), right after the existing scheduler.add_job call:
#
#   # Daily report — every day at 08:00 Moscow time (05:00 UTC)
#   scheduler.add_job(
#       lambda: asyncio.create_task(send_daily_report(bot, ADMIN_CHAT_ID, DB_PATH)),
#       CronTrigger(hour=5, minute=0),
#       id='daily_report',
#       replace_existing=True,
#   )
#
#   # Weekly summary — every Monday at 07:05 UTC (right after the weekly digest at 07:00)
#   scheduler.add_job(
#       lambda: asyncio.create_task(send_weekly_summary(bot, ADMIN_CHAT_ID, DB_PATH)),
#       CronTrigger(day_of_week='mon', hour=7, minute=5),
#       id='weekly_summary',
#       replace_existing=True,
#   )
#
# ══════════════════════════════════════════════════════════════════════════════


# ── Standalone runner (no bot instance needed) ─────────────────────────────
async def _send_standalone() -> None:
    """Run the daily report without an aiogram bot instance — uses raw HTTP."""
    import aiohttp

    # Load .env if running standalone
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    k = k.strip()
                    if k.replace("_", "").isalnum():
                        os.environ.setdefault(k, v.strip())

    token     = os.getenv("BOT_TOKEN", "")
    admin_id  = int(os.getenv("ADMIN_ID", str(ADMIN_CHAT_ID)))

    if not token:
        print("ERROR: BOT_TOKEN not set")
        return

    # Build a fake bot-like object that sends via HTTP
    class _HttpBot:
        def __init__(self, tok):
            self._tok = tok
            self._url = f"https://api.telegram.org/bot{tok}/sendMessage"

        async def send_message(self, chat_id, text, parse_mode="HTML", **kw):
            async with aiohttp.ClientSession() as s:
                r = await s.post(self._url, json={
                    "chat_id": chat_id, "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                })
                data = await r.json()
                if not data.get("ok"):
                    print(f"Telegram error: {data}")
                else:
                    print(f"✅ Report sent to {chat_id}")
                return data

    bot = _HttpBot(token)
    await send_daily_report(bot, admin_id)


if __name__ == "__main__":
    import asyncio
    asyncio.run(_send_standalone())
