"""
checkin.py — T+24h onboarding check-in for new bot users.

Sends "Did you finish your resume?" exactly once, 23-26 hours after signup.
Routes "Got stuck" responses to the admin in real-time.
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot, Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select

from database.db import get_session
from models.user import User

router = Router()
logger = logging.getLogger(__name__)

ADMIN_ID = int(os.getenv("ADMIN_ID", "0")))

CHECKIN_TEXT = (
    "👋 <b>Как дела с резюме?</b>\n\n"
    "Вы зарегистрировались вчера — просто хотел убедиться, что всё получилось.\n\n"
    "Успели создать резюме?"
)


def checkin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, готово!", callback_data="checkin:done"),
            InlineKeyboardButton(text="🔄 Ещё работаю", callback_data="checkin:wip"),
        ],
        [
            InlineKeyboardButton(text="🆘 Застрял, помоги", callback_data="checkin:stuck"),
        ],
    ])


async def send_24h_checkins(bot: Bot) -> None:
    """Find users in the 23-26h window since signup who haven't been checked in, send them the message."""
    now = datetime.utcnow()
    window_start = now - timedelta(hours=26)
    window_end   = now - timedelta(hours=23)

    async with get_session() as session:
        result = await session.execute(
            select(User).where(
                User.created_at >= window_start,
                User.created_at <= window_end,
                User.checkin_sent_at.is_(None),
            )
        )
        users = result.scalars().all()

    for user in users:
        try:
            await bot.send_message(
                user.telegram_id,
                CHECKIN_TEXT,
                reply_markup=checkin_kb(),
                parse_mode="HTML",
            )
            # Mark as sent
            async with get_session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == user.telegram_id)
                )
                u = result.scalar_one_or_none()
                if u:
                    u.checkin_sent_at = now
            logger.info("[checkin] sent to user %d (%s)", user.telegram_id, user.username)
        except Exception as exc:
            # User may have blocked the bot — mark sent anyway to avoid retrying
            logger.warning("[checkin] failed for user %d: %s", user.telegram_id, exc)
            async with get_session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == user.telegram_id)
                )
                u = result.scalar_one_or_none()
                if u:
                    u.checkin_sent_at = now  # don't retry on blocked users


async def checkin_loop(bot: Bot) -> None:
    """Background task: poll every 30 min for users ready for their T+24h check-in."""
    await asyncio.sleep(300)  # wait 5 min after bot startup before first scan
    while True:
        try:
            await send_24h_checkins(bot)
        except Exception as exc:
            logger.error("[checkin] loop error: %s", exc)
        await asyncio.sleep(1800)  # every 30 minutes


# ── Callback handlers ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "checkin:done")
async def checkin_done(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "🎉 <b>Отлично, поздравляю!</b>\n\n"
        "Несколько следующих шагов:\n"
        "• <b>Скачайте PDF</b> и сохраните копию\n"
        "• <b>Создайте сопроводительное письмо</b> — /cover\n"
        "• <b>Настройте авто-отклики</b> на hh.ru — resumeai-bot.ru\n\n"
        "Удачи в поиске работы! 💪",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "checkin:wip")
async def checkin_wip(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "👍 <b>Всё идёт по плану!</b>\n\n"
        "Если возникнут вопросы — я здесь:\n"
        "• Напишите /help — список команд\n"
        "• Задайте любой вопрос прямо в чат\n\n"
        "Отвечаю в течение часа 🕐",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "checkin:stuck")
async def checkin_stuck(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    user = callback.from_user
    name = user.full_name or user.username or str(user.id)

    # Immediately ping the admin
    try:
        await bot.send_message(
            ADMIN_ID,
            f"🆘 <b>Пользователь застрял при создании резюме!</b>\n\n"
            f"👤 {name} (@{user.username or '—'})\n"
            f"🆔 <code>{user.id}</code>\n\n"
            f"Ответь им лично в течение часа.",
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.error("[checkin] admin ping failed: %s", exc)

    await callback.message.edit_text(
        "🆘 <b>Основатель уже получил уведомление!</b>\n\n"
        "Максим свяжется с вами лично в течение часа и поможет разобраться.\n\n"
        "Или напишите прямо сейчас: @maksimabramov",
        parse_mode="HTML",
    )
