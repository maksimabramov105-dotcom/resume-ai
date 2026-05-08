"""
auto_apply.py — Telegram handler for the 🚀 Auto-Apply button.

Opens the web dashboard /app where users manage auto-apply campaigns.
Also shows quick tips so users know what to expect.
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import WEBAPP_URL
from database.db import get_or_create_user
from utils.bot_translations import t

router = Router()

_BASE_APP_URL = (WEBAPP_URL or "https://resumeai-bot.ru").rstrip("/") + "/app"


def _build_app_url(telegram_id: int) -> str:
    """Return /app/auth?t=<token> when LINK_SECRET is set, else /app."""
    try:
        from services.link_token import issue_link_token
        token = issue_link_token(telegram_id)
        return f"{_BASE_APP_URL}/auth?t={token}"
    except Exception:
        return _BASE_APP_URL


def _auto_apply_kb(lang: str, telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(lang, 'auto_apply.open_btn'),
            url=_build_app_url(telegram_id),
        )],
        [InlineKeyboardButton(text=t(lang, 'btn.menu'), callback_data="main_menu")],
    ])


@router.callback_query(lambda c: c.data == "auto_apply")
async def auto_apply_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    try:
        from bot.analytics import track as _ph_track
        _ph_track(callback.from_user.id, 'auto_apply_started', {'target_count': user.daily_limit if hasattr(user, 'daily_limit') else 0})
    except Exception:
        pass
    await callback.message.edit_text(
        t(lang, 'auto_apply.info'),
        parse_mode="HTML",
        reply_markup=_auto_apply_kb(lang, callback.from_user.id),
    )


@router.message(Command("autoapply"))
async def auto_apply_command(message: Message):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'en'
    try:
        from bot.analytics import track as _ph_track
        _ph_track(message.from_user.id, 'auto_apply_started', {'target_count': user.daily_limit if hasattr(user, 'daily_limit') else 0})
    except Exception:
        pass
    await message.answer(
        t(lang, 'auto_apply.info'),
        parse_mode="HTML",
        reply_markup=_auto_apply_kb(lang, message.from_user.id),
    )
