"""
checkin.py — T+24h onboarding check-in for new bot users.

Sends "Did you finish your resume?" exactly once, 23-26 hours after signup.
Routes "Got stuck" responses to the admin in real-time.
Bilingual: respects user.language (en default, ru override).
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

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ── Bilingual strings ─────────────────────────────────────────────────────────

_CHECKIN_TEXT = {
    "en": (
        "👋 <b>How's the resume going?</b>\n\n"
        "You signed up yesterday — just checking that everything worked out.\n\n"
        "Did you manage to create your resume?"
    ),
    "ru": (
        "👋 <b>Как дела с резюме?</b>\n\n"
        "Вы зарегистрировались вчера — просто хотел убедиться, что всё получилось.\n\n"
        "Успели создать резюме?"
    ),
}

_BTN_DONE = {"en": "✅ Yes, done!", "ru": "✅ Да, готово!"}
_BTN_WIP  = {"en": "🔄 Still working", "ru": "🔄 Ещё работаю"}
_BTN_STUCK = {"en": "🆘 I'm stuck, help!", "ru": "🆘 Застрял, помоги"}

_DONE_TEXT = {
    "en": (
        "🎉 <b>Great, congratulations!</b>\n\n"
        "Next steps:\n"
        "• <b>Download the PDF</b> and keep a copy\n"
        "• <b>Write a cover letter</b> — /cover\n"
        "• <b>Set up auto-apply</b> on LinkedIn, Indeed — resumeai-bot.ru\n\n"
        "Good luck with your job search! 💪"
    ),
    "ru": (
        "🎉 <b>Отлично, поздравляю!</b>\n\n"
        "Несколько следующих шагов:\n"
        "• <b>Скачайте PDF</b> и сохраните копию\n"
        "• <b>Создайте сопроводительное письмо</b> — /cover\n"
        "• <b>Настройте авто-отклики</b> на LinkedIn, Indeed — resumeai-bot.ru\n\n"
        "Удачи в поиске работы! 💪"
    ),
}

_WIP_TEXT = {
    "en": (
        "👍 <b>All going to plan!</b>\n\n"
        "If you have questions — I'm here:\n"
        "• Type /help — list of commands\n"
        "• Ask anything directly in the chat\n\n"
        "I reply within an hour 🕐"
    ),
    "ru": (
        "👍 <b>Всё идёт по плану!</b>\n\n"
        "Если возникнут вопросы — я здесь:\n"
        "• Напишите /help — список команд\n"
        "• Задайте любой вопрос прямо в чат\n\n"
        "Отвечаю в течение часа 🕐"
    ),
}

_STUCK_TEXT = {
    "en": (
        "🆘 <b>The founder has been notified!</b>\n\n"
        "Maksim will reach out to you personally within an hour.\n\n"
        "Or write right now: @maksimabramov"
    ),
    "ru": (
        "🆘 <b>Основатель уже получил уведомление!</b>\n\n"
        "Максим свяжется с вами лично в течение часа и поможет разобраться.\n\n"
        "Или напишите прямо сейчас: @maksimabramov"
    ),
}

_ADMIN_STUCK = {
    "en": (
        "🆘 <b>User stuck creating their resume!</b>\n\n"
        "👤 {name} (@{username})\n"
        "🆔 <code>{uid}</code>\n\n"
        "Reply to them personally within an hour."
    ),
    "ru": (
        "🆘 <b>Пользователь застрял при создании резюме!</b>\n\n"
        "👤 {name} (@{username})\n"
        "🆔 <code>{uid}</code>\n\n"
        "Ответь им лично в течение часа."
    ),
}


def _lang(user: User | None) -> str:
    if user and user.language in ("ru", "en"):
        return user.language
    return "en"


def checkin_kb(lang: str = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=_BTN_DONE[lang],  callback_data="checkin:done"),
            InlineKeyboardButton(text=_BTN_WIP[lang],   callback_data="checkin:wip"),
        ],
        [
            InlineKeyboardButton(text=_BTN_STUCK[lang], callback_data="checkin:stuck"),
        ],
    ])


async def _get_user_lang(telegram_id: int) -> str:
    """Look up a user's language preference from the DB."""
    try:
        async with get_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            u = result.scalar_one_or_none()
            return _lang(u)
    except Exception:
        return "en"


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
            lang = _lang(user)
            await bot.send_message(
                user.telegram_id,
                _CHECKIN_TEXT[lang],
                reply_markup=checkin_kb(lang),
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
            logger.info("[checkin] sent to user %d (%s) [%s]", user.telegram_id, user.username, lang)
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
    lang = await _get_user_lang(callback.from_user.id)
    await callback.message.edit_text(_DONE_TEXT[lang], parse_mode="HTML")


@router.callback_query(F.data == "checkin:wip")
async def checkin_wip(callback: CallbackQuery):
    await callback.answer()
    lang = await _get_user_lang(callback.from_user.id)
    await callback.message.edit_text(_WIP_TEXT[lang], parse_mode="HTML")


@router.callback_query(F.data == "checkin:stuck")
async def checkin_stuck(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    lang = await _get_user_lang(callback.from_user.id)
    user = callback.from_user
    name = user.full_name or user.username or str(user.id)

    # Immediately ping the admin
    try:
        await bot.send_message(
            ADMIN_ID,
            _ADMIN_STUCK["en"].format(name=name, username=user.username or "—", uid=user.id),
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.error("[checkin] admin ping failed: %s", exc)

    await callback.message.edit_text(_STUCK_TEXT[lang], parse_mode="HTML")
