"""
Language selection handler.

Handles:
  /language command  — show language picker at any time
  lang:ru / lang:en  callback data — save choice, then ask for email (new users)
  email input        — save email, show main menu
  skip_email         — skip email step, show main menu
"""
from __future__ import annotations

import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class OnboardingStates(StatesGroup):
    waiting_email = State()


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English",  callback_data="lang:en"),
        ]
    ])


def _skip_kb(lang: str) -> InlineKeyboardMarkup:
    label = "Пропустить →" if lang == 'ru' else "Skip →"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data="skip_email")]
    ])


def _email_ask_text(lang: str) -> str:
    if lang == 'ru':
        return (
            "📧 <b>Введите ваш email</b>\n\n"
            "Будем присылать советы по поиску работы и уведомления об обновлениях.\n"
            "Можно пропустить — это необязательно."
        )
    return (
        "📧 <b>What's your email?</b>\n\n"
        "We'll send job search tips and product updates.\n"
        "Totally optional — tap Skip if you prefer."
    )


@router.message(Command("language"))
async def cmd_language(message: Message) -> None:
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'lang.choose'), reply_markup=language_kb())


async def _after_lang(callback: CallbackQuery, state: FSMContext, lang: str) -> None:
    """Shared logic: save language, then ask for email or go straight to menu."""
    user = await get_or_create_user(callback.from_user.id)
    user.language = lang
    await save_user(user)
    await callback.answer()

    if user.email:
        # Existing user changing language — skip email step
        key = 'lang.set_ru' if lang == 'ru' else 'lang.set_en'
        await callback.message.edit_text(
            t(lang, key) + "\n\n" + t(lang, 'start.welcome'),
            reply_markup=main_menu_kb(lang),
        )
        return

    await state.set_state(OnboardingStates.waiting_email)
    await state.update_data(lang=lang)
    await callback.message.edit_text(
        _email_ask_text(lang),
        parse_mode="HTML",
        reply_markup=_skip_kb(lang),
    )


@router.callback_query(F.data == "lang:ru")
async def set_lang_ru(callback: CallbackQuery, state: FSMContext) -> None:
    await _after_lang(callback, state, 'ru')


@router.callback_query(F.data == "lang:en")
async def set_lang_en(callback: CallbackQuery, state: FSMContext) -> None:
    await _after_lang(callback, state, 'en')


@router.message(OnboardingStates.waiting_email, F.text)
async def got_email(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    email = message.text.strip()

    if not _EMAIL_RE.match(email):
        bad = "❌ Неверный формат. Попробуйте ещё раз или нажмите «Пропустить»." if lang == 'ru' \
              else "❌ Invalid email format. Try again or tap Skip."
        await message.answer(bad, reply_markup=_skip_kb(lang))
        return

    user = await get_or_create_user(message.from_user.id)
    user.email = email
    await save_user(user)
    await state.clear()

    ok = "✅ Email сохранён!\n\n" if lang == 'ru' else "✅ Email saved!\n\n"
    await message.answer(
        ok + t(lang, 'start.welcome'),
        reply_markup=main_menu_kb(lang),
    )

    try:
        from bot.analytics import track as _ph_track
        _ph_track(message.from_user.id, 'email_collected', {})
    except Exception:
        pass


@router.callback_query(F.data == "skip_email")
async def skip_email(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get('lang', 'ru')
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        t(lang, 'start.welcome'),
        reply_markup=main_menu_kb(lang),
    )
