"""
auto_apply.py — Telegram handler for the 🚀 Auto-Apply button.

Opens the web dashboard /app where users manage auto-apply campaigns.
Also shows quick tips so users know what to expect.
"""
import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.user_service import get_or_create_user
from utils.bot_translations import t

router = Router()

WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "https://resumeai-bot.ru")
APP_URL = WEBAPP_BASE_URL.rstrip("/") + "/app"


def _auto_apply_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=t(lang, 'auto_apply.open_btn'),
            url=APP_URL,
        )],
        [InlineKeyboardButton(text=t(lang, 'btn.menu'), callback_data="main_menu")],
    ])


@router.callback_query(lambda c: c.data == "auto_apply")
async def auto_apply_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    await callback.message.edit_text(
        t(lang, 'auto_apply.info'),
        parse_mode="HTML",
        reply_markup=_auto_apply_kb(lang),
    )


@router.message(Command("autoapply"))
async def auto_apply_command(message: Message):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'ru'
    await message.answer(
        t(lang, 'auto_apply.info'),
        parse_mode="HTML",
        reply_markup=_auto_apply_kb(lang),
    )
