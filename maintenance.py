"""
maintenance.py — Maintenance mode + user notification system.

MAINTENANCE MODE:
  - Set MAINTENANCE=1 in .env  →  all bot handlers show maintenance message
  - Set MAINTENANCE=0 or remove →  bot works normally

BROADCAST:
  - broadcast_maintenance_start(bot)  →  tells all active users "server down"
  - broadcast_maintenance_end(bot)    →  tells all active users "everything is fixed"

Integrated into run.py via the error middleware and startup check.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta

import aiosqlite

log = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────────────
MAINTENANCE_MODE = os.getenv("MAINTENANCE", "0").strip() in ("1", "true", "yes")
BOT_TOKEN        = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID    = int(os.getenv("ADMIN_ID", "0")))
BOT_DB           = os.getenv("BOT_DB", "/opt/resumeaibot/bot.db")

MAINTENANCE_TEXT = (
    "⚙️ <b>Технические работы</b>\n\n"
    "На сервере сейчас временный сбой — мы уже в курсе и активно чиним.\n\n"
    "Все ваши данные в безопасности. Бот вернётся в работу в ближайшее время.\n\n"
    "Приносим извинения за неудобства! 🙏"
)

RECOVERY_TEXT = (
    "✅ <b>Всё работает!</b>\n\n"
    "Сервер восстановлен, бот снова в строю.\n"
    "Можете продолжать пользоваться всеми функциями.\n\n"
    "Спасибо за терпение! 💪"
)


def is_maintenance() -> bool:
    """Re-reads env var at call time so changes take effect without restart."""
    return os.getenv("MAINTENANCE", "0").strip() in ("1", "true", "yes")


async def get_all_active_user_ids(db_path: str = BOT_DB) -> list[int]:
    """
    Returns telegram_ids of users who were active in the last 30 days.
    Limits to 1000 to avoid hitting Telegram rate limits.
    """
    cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                """SELECT DISTINCT telegram_id FROM users
                   WHERE created_at >= ? OR telegram_id IN (
                       SELECT DISTINCT telegram_id FROM generation_logs
                       WHERE created_at >= ?
                   )
                   LIMIT 1000""",
                (cutoff, cutoff),
            ) as cur:
                rows = await cur.fetchall()
        return [r[0] for r in rows if r[0]]
    except Exception as e:
        log.error("get_all_active_user_ids failed: %s", e)
        return []


async def broadcast(bot, text: str, exclude_admin: bool = False) -> tuple[int, int]:
    """
    Send a message to all recently active users.
    Returns (sent_count, failed_count).
    Respects Telegram rate limit: max 30 messages/second.
    """
    user_ids = await get_all_active_user_ids()
    if not exclude_admin and ADMIN_CHAT_ID not in user_ids:
        user_ids = [ADMIN_CHAT_ID] + user_ids

    sent = failed = 0
    for i, uid in enumerate(user_ids):
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            sent += 1
        except Exception as e:
            log.warning("Broadcast failed for user %s: %s", uid, e)
            failed += 1
        # Rate limit: 25 msg/sec (Telegram allows 30, leave headroom)
        if (i + 1) % 25 == 0:
            await asyncio.sleep(1.0)

    log.info("Broadcast done: sent=%d failed=%d", sent, failed)
    return sent, failed


async def broadcast_maintenance_start(bot) -> None:
    """Notify all active users that maintenance has started."""
    log.info("Broadcasting maintenance start to all users…")
    sent, failed = await broadcast(bot, MAINTENANCE_TEXT)
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"📢 Maintenance broadcast sent: {sent} delivered, {failed} failed.",
    )


async def broadcast_maintenance_end(bot) -> None:
    """Notify all active users that everything is back to normal."""
    log.info("Broadcasting maintenance end (recovery) to all users…")
    sent, failed = await broadcast(bot, RECOVERY_TEXT)
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"✅ Recovery broadcast sent: {sent} delivered, {failed} failed.",
    )
