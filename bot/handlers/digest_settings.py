"""
digest_settings.py — /digest command: enable/disable daily job digest.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.db import get_or_create_user
from utils.bot_translations import t

router = Router()


def _digest_kb(enabled: bool, lang: str) -> InlineKeyboardMarkup:
    if enabled:
        label = "🔕 Disable daily digest" if lang == "en" else "🔕 Выключить рассылку вакансий"
        cb = "digest:off"
    else:
        label = "🔔 Enable daily digest" if lang == "en" else "🔔 Включить рассылку вакансий"
        cb = "digest:on"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=cb)],
        [InlineKeyboardButton(
            text="◀️ Menu" if lang == "en" else "◀️ Меню",
            callback_data="main_menu",
        )],
    ])


@router.message(Command("digest"))
async def digest_command(message: Message):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or "en"
    enabled = bool(getattr(user, "digest_enabled", 1))

    if lang == "en":
        status = "✅ active" if enabled else "❌ disabled"
        text = (
            f"📬 <b>Daily Job Digest</b>\n\n"
            f"Status: {status}\n\n"
            "Every morning I'll send you the top 5 matching job openings based on your profile.\n"
            "Make sure your specialty is set in your /profile."
        )
    else:
        status = "✅ включена" if enabled else "❌ выключена"
        text = (
            f"📬 <b>Ежедневная подборка вакансий</b>\n\n"
            f"Статус: {status}\n\n"
            "Каждое утро я буду присылать топ-5 подходящих вакансий по вашему профилю.\n"
            "Убедитесь, что специальность указана в /profile."
        )

    await message.answer(text, reply_markup=_digest_kb(enabled, lang))


@router.callback_query(F.data.in_({"digest:on", "digest:off"}))
async def toggle_digest_callback(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or "en"
    new_enabled = callback.data == "digest:on"

    from services.job_digest import toggle_digest
    await toggle_digest(callback.from_user.id, new_enabled)

    await callback.answer()

    if lang == "en":
        msg = "🔔 Daily digest enabled!" if new_enabled else "🔕 Daily digest disabled."
    else:
        msg = "🔔 Рассылка вакансий включена!" if new_enabled else "🔕 Рассылка вакансий выключена."

    await callback.message.edit_text(msg, reply_markup=_digest_kb(new_enabled, lang))
