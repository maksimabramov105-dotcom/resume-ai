"""
Support handler — lets users send feedback/questions directly to the admin.
"""
from __future__ import annotations

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from utils.keyboards import main_menu_kb, support_kb
from utils.texts import SUPPORT_MESSAGE, SUPPORT_SENT, ADMIN_SUPPORT_NOTIFY

router = Router()


class SupportStates(StatesGroup):
    waiting_message = State()


# ── Open support ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "support")
async def open_support(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_message)
    await callback.message.edit_text(SUPPORT_MESSAGE, reply_markup=support_kb())


# ── Receive support message ───────────────────────────────────────────────────

@router.message(SupportStates.waiting_message, F.text)
async def got_support_message(message: Message, state: FSMContext, bot: Bot):
    await state.clear()

    # Forward to admin
    notify = ADMIN_SUPPORT_NOTIFY.format(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name or "—",
        username=message.from_user.username or "—",
        text=message.text,
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            notify,
            reply_markup=_reply_kb(message.from_user.id),
        )
    except Exception:
        pass

    await message.answer(SUPPORT_SENT, reply_markup=main_menu_kb())


@router.message(SupportStates.waiting_message, F.photo)
async def got_support_photo(message: Message, state: FSMContext, bot: Bot):
    """User sent a photo (e.g. bug screenshot) with optional caption."""
    await state.clear()

    caption_text = message.caption or "(без подписи)"
    notify = ADMIN_SUPPORT_NOTIFY.format(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name or "—",
        username=message.from_user.username or "—",
        text=f"[фото] {caption_text}",
    )
    try:
        await bot.send_photo(
            ADMIN_ID,
            photo=message.photo[-1].file_id,
            caption=notify[:1020],
            reply_markup=_reply_kb(message.from_user.id),
        )
    except Exception:
        pass

    await message.answer(SUPPORT_SENT, reply_markup=main_menu_kb())


@router.message(SupportStates.waiting_message)
async def support_wrong_type(message: Message):
    await message.answer("📝 Пожалуйста, напиши текстовое сообщение или прикрепи фото.")


# ── Admin replies to support message ──────────────────────────────────────────

@router.callback_query(F.data.startswith("reply_user:"))
async def admin_reply_prompt(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await state.set_state(SupportStates.waiting_message)
    await state.update_data(reply_to_user_id=user_id)
    await callback.message.answer(
        f"✏️ Напиши ответ пользователю <code>{user_id}</code>:"
    )
    await callback.answer()


@router.message(SupportStates.waiting_message, F.text)
async def admin_send_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    reply_user_id = data.get("reply_to_user_id")

    if not reply_user_id:
        # Regular user support message (handled above)
        return

    await state.clear()
    try:
        await bot.send_message(
            reply_user_id,
            f"💬 <b>Ответ поддержки:</b>\n\n{message.text}",
        )
        await message.answer("✅ Ответ отправлен пользователю.")
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить: {e}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reply_kb(user_id: int):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="↩️ Ответить пользователю",
            callback_data=f"reply_user:{user_id}",
        )],
    ])
