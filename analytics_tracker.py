"""
analytics_tracker.py — Non-invasive real-time event tracking for РезюмеАИ bot.

Rules:
  - Every function wraps ALL logic in try/except
  - A tracking failure NEVER raises — only logs a warning
  - Each function adds exactly ONE aiosqlite connection (no shared state)
  - No new APScheduler, no new event loop, no new threads

See INTEGRATION INSTRUCTIONS at the bottom of this file for exactly where
to add each call in the existing handlers.
"""

import aiosqlite
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Same path used by analytics_db.py — must match
DB_PATH = "/opt/resumeaibot/bot.db"

# Feature name → daily_stats column mapping
_FEATURE_COL = {
    "resume":           "resumes_generated",
    "cover_letter":     "letters_generated",
    "interview":        "interviews_done",
    "vacancy_analysis": "vacancy_analyses",
    "ai_message":       "ai_messages",
}

# Payment method → daily_stats column mapping
_REVENUE_COL = {
    "crypto":  "revenue_crypto",
    "card":    "revenue_card",
    "revolut": "revenue_revolut",
}


async def _ensure_today_row(db: aiosqlite.Connection, today: str) -> None:
    """
    Guarantees a row exists for today in daily_stats before we UPDATE it.
    Uses INSERT OR IGNORE so concurrent calls are safe.
    """
    await db.execute(
        "INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (today,)
    )


# ── Public tracking functions ─────────────────────────────────────────────────

async def track_start(user_id: int, payload: str, db_path: str = DB_PATH) -> None:
    """
    Called once per /start invocation to record how the user found the bot.

    Detects source from the deep-link payload:
      - starts with "ref_"  → "referral"
      - contains "reddit"   → "reddit"
      - contains "vk"       → "vk"
      - contains "directory"→ "directory"
      - contains "outreach" → "outreach"
      - anything else       → "direct"

    Inserts into join_sources (INSERT OR IGNORE — only the FIRST visit is kept).
    """
    try:
        p = (payload or "").lower()
        if p.startswith("ref_"):
            source = "referral"
        elif "reddit" in p:
            source = "reddit"
        elif "vk" in p:
            source = "vk"
        elif "directory" in p:
            source = "directory"
        elif "outreach" in p:
            source = "outreach"
        else:
            source = "direct"

        today = date.today().isoformat()
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO join_sources (user_id, source, recorded_at) VALUES (?,?,?)",
                (user_id, source, today)
            )
            await db.commit()
    except Exception as exc:
        logger.warning("track_start failed (user=%s): %s", user_id, exc)


async def track_payment(
    user_id: int, amount: float, method: str, db_path: str = DB_PATH
) -> None:
    """
    Call this immediately after a payment is confirmed to update today's
    revenue totals in daily_stats.

    method must be one of: "crypto", "card", "revolut"
    amount is in RUB (matches the amount_rub column in payments table).
    """
    try:
        col = _REVENUE_COL.get(method)
        if not col:
            logger.warning("track_payment: unknown method '%s' for user %s", method, user_id)
            return

        today = date.today().isoformat()
        async with aiosqlite.connect(db_path) as db:
            await _ensure_today_row(db, today)
            # Increment with SQL to avoid race conditions between concurrent requests
            await db.execute(
                f"UPDATE daily_stats SET {col} = {col} + ? WHERE date = ?",
                (float(amount), today)
            )
            await db.commit()
    except Exception as exc:
        logger.warning("track_payment failed (user=%s, method=%s): %s", user_id, method, exc)


async def track_feature(
    user_id: int, feature: str, db_path: str = DB_PATH
) -> None:
    """
    Call this after any AI generation completes to increment today's
    feature usage counter in daily_stats.

    feature must be one of:
      "resume" | "cover_letter" | "interview" | "vacancy_analysis" | "ai_message"
    """
    try:
        col = _FEATURE_COL.get(feature)
        if not col:
            logger.warning("track_feature: unknown feature '%s' for user %s", feature, user_id)
            return

        today = date.today().isoformat()
        async with aiosqlite.connect(db_path) as db:
            await _ensure_today_row(db, today)
            await db.execute(
                f"UPDATE daily_stats SET {col} = {col} + 1 WHERE date = ?",
                (today,)
            )
            await db.commit()
    except Exception as exc:
        logger.warning("track_feature failed (user=%s, feature=%s): %s", user_id, feature, exc)


def generate_referral_link(user_id: int) -> str:
    """
    Returns the shareable deep-link for this user.
    Pure function — no DB call, no await needed.
    """
    return f"https://t.me/topbestworkerbot?start=ref_{user_id}"


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION INSTRUCTIONS
# Copy-paste exactly these lines into the handlers listed below.
# Each addition is a single await call that never breaks the parent handler.
# ══════════════════════════════════════════════════════════════════════════════

# ─── 1. /start handler ────────────────────────────────────────────────────────
# File: bot/handlers/start.py  →  cmd_start()
# Add AFTER `user = await get_or_create_user(...)` and AFTER referral handling:
#
#   from analytics_tracker import track_start, DB_PATH
#   await track_start(user.telegram_id, args, DB_PATH)
#
# Full context:
#   user = await get_or_create_user(telegram_id=message.from_user.id, ...)
#   # ... referral block ...
#   await track_start(user.telegram_id, args, DB_PATH)    # ← ADD HERE
#   await message.answer(START_MESSAGE, reply_markup=main_menu_kb())

# ─── 2. Crypto payment confirmed ──────────────────────────────────────────────
# File: bot/handlers/payment.py  →  check_crypto()
# Add AFTER `await update_payment_status(invoice_id, "succeeded")`:
#
#   from analytics_tracker import track_payment, DB_PATH
#   await track_payment(callback.from_user.id, pkg["price_rub"], "crypto", DB_PATH)

# ─── 3. Manual card/Revolut — AI auto-approved ────────────────────────────────
# File: bot/handlers/payment.py  →  got_receipt(), inside `if ai_result.verdict == "approve":`
# Add AFTER `await update_payment_status_by_id(payment_db_id, "succeeded")`:
#
#   from analytics_tracker import track_payment, DB_PATH
#   _track_method = "revolut" if payment_method == "revolut" else "card"
#   await track_payment(message.from_user.id, pkg.get("price_rub", 0), _track_method, DB_PATH)

# ─── 4. Manual card/Revolut — admin approved ──────────────────────────────────
# File: bot/handlers/payment.py  →  admin_approve()
# Add AFTER `await update_payment_status_by_id(payment_db_id, "succeeded")`:
#
#   from analytics_tracker import track_payment, DB_PATH
#   # Admin approval doesn't have method context — track as "card" (conservative)
#   pkg_info = PRICING.get(package_key, {"price_rub": 0})
#   await track_payment(telegram_id, pkg_info["price_rub"], "card", DB_PATH)

# ─── 5. Feature: Resume ───────────────────────────────────────────────────────
# File: bot/handlers/resume.py  →  _generate_and_send()
# Add AFTER `resume_text, tokens = await generate_resume(...)`:
#
#   from analytics_tracker import track_feature, DB_PATH
#   await track_feature(message.from_user.id, "resume", DB_PATH)

# ─── 6. Feature: Cover Letter ─────────────────────────────────────────────────
# File: bot/handlers/cover_letter.py  →  got_vacancy()
# Add AFTER `letter_text, tokens = await generate_cover_letter(...)`:
#
#   from analytics_tracker import track_feature, DB_PATH
#   await track_feature(message.from_user.id, "cover_letter", DB_PATH)

# ─── 7. Feature: Interview ────────────────────────────────────────────────────
# File: bot/handlers/interview.py  →  finish_interview_handler()
# Add AFTER `final_text, tokens = await finish_interview(...)`:
#
#   from analytics_tracker import track_feature, DB_PATH
#   await track_feature(callback.from_user.id, "interview", DB_PATH)

# ─── 8. Feature: Vacancy Analysis ────────────────────────────────────────────
# File: bot/handlers/vacancy_analysis.py  →  got_vacancy()
# Add AFTER `analysis_text, tokens = await analyze_vacancy(vacancy)`:
#
#   from analytics_tracker import track_feature, DB_PATH
#   await track_feature(message.from_user.id, "vacancy_analysis", DB_PATH)

# ─── 9. Feature: AI Assistant ─────────────────────────────────────────────────
# File: bot/handlers/ai_assistant.py  →  handle_assistant_message()
# Add AFTER `response, tokens = await chat_completion(...)`:
#
#   from analytics_tracker import track_feature, DB_PATH
#   await track_feature(message.from_user.id, "ai_message", DB_PATH)

# ══════════════════════════════════════════════════════════════════════════════
