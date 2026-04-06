"""
Weekly career digest — sends personalised career tips every Monday at 10:00 MSK.
Uses APScheduler with asyncio.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


async def get_weekly_tip(specialty: Optional[str], skills: Optional[str]) -> str:
    """Generate a personalised weekly career tip via OpenRouter."""
    from services.openai_service import chat_completion

    profile = ""
    if specialty:
        profile += f"Специальность: {specialty}. "
    if skills:
        profile += f"Навыки: {skills[:200]}."

    prompt = (
        f"Дай короткий (3-5 абзацев) еженедельный карьерный совет для специалиста. "
        f"{profile if profile else 'Универсальный совет для любого специалиста.'}\n\n"
        "Формат: эмодзи + конкретный actionable совет. Никаких воды и клише. "
        "Пиши как умный друг, который знает HR-индустрию."
    )

    result, _ = await chat_completion([{"role": "user", "content": prompt}], max_tokens=400)
    return result


async def send_weekly_digest(bot) -> None:
    """Send weekly digest to all active users."""
    from database.db import get_all_users

    logger.info("Starting weekly digest...")
    users = await get_all_users()
    sent = 0
    failed = 0

    for user in users:
        try:
            tip = await get_weekly_tip(
                specialty=getattr(user, 'specialty', None),
                skills=user.skills_text,
            )
            text = (
                "📬 <b>Еженедельный карьерный совет</b>\n\n"
                f"{tip}\n\n"
                "<i>РезюмеАИ — с нами шансы найти работу 100% 🎯</i>"
            )
            await bot.send_message(user.telegram_id, text)
            sent += 1
        except Exception as e:
            failed += 1
            logger.debug("Digest failed for %s: %s", user.telegram_id, e)

    logger.info("Weekly digest done. Sent: %d, Failed: %d", sent, failed)
