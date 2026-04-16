"""
Language selection handler.

Handles:
  /language command  — show language picker at any time
  lang:ru / lang:en  callback data — save choice and show main menu
"""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from database.db import get_or_create_user, save_user
from utils.bot_translations import t
from utils.keyboards import main_menu_kb

router = Router()


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English",  callback_data="lang:en"),
        ]
    ])


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'lang.choose'), reply_markup=language_kb())


@router.callback_query(F.data == "lang:ru")
async def set_lang_ru(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id)
    user.language = 'ru'
    await save_user(user)
    await callback.answer()
    await callback.message.edit_text(
        t('ru', 'lang.set_ru') + "\n\n" + t('ru', 'start.welcome'),
        reply_markup=main_menu_kb('ru'),
    )


@router.callback_query(F.data == "lang:en")
async def set_lang_en(callback: CallbackQuery) -> None:
    user = await get_or_create_user(callback.from_user.id)
    user.language = 'en'
    await save_user(user)
    await callback.answer()
    await callback.message.edit_text(
        t('en', 'lang.set_en') + "\n\n" + t('en', 'start.welcome'),
        reply_markup=main_menu_kb('en'),
    )
