"""
Support handler — lets users send feedback/questions directly to the admin.
Also provides /help command with 5 knowledge base articles.
"""
from __future__ import annotations

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_ID
from utils.keyboards import main_menu_kb, support_kb
from utils.texts import SUPPORT_MESSAGE, SUPPORT_SENT, ADMIN_SUPPORT_NOTIFY

router = Router()

# ── Knowledge base ────────────────────────────────────────────────────────────

_KB_ARTICLES = {
    "kb:pdf": (
        "📄 <b>Как скачать резюме в PDF</b>",
        "1. Создайте резюме через /resume\n"
        "2. Нажмите кнопку <b>«📄 Скачать PDF»</b> — файл придёт в чат\n"
        "3. На сайте: кнопка <b>«Экспорт PDF»</b> в правом верхнем углу\n\n"
        "<b>PDF не скачивается?</b> Обновите страницу или напишите @maksimabramov — "
        "отвечаем в течение часа 🕐"
    ),
    "kb:format": (
        "🎨 <b>Форматирование выглядит неправильно</b>",
        "Частые причины:\n"
        "• <b>Текст слишком длинный</b> — сократите до 1-2 страниц\n"
        "• <b>Много символов</b> •→★ — замените на тире и цифры\n"
        "• <b>Не тот шаблон</b> — попробуйте «Классический» или «ATS-оптимизированный»\n\n"
        "Нажмите <b>«Сгенерировать заново»</b> в редакторе — AI пересоздаст с чистой структурой."
    ),
    "kb:templates": (
        "🖼 <b>Как сменить шаблон резюме</b>",
        "В боте: /resume → <b>«Сменить шаблон»</b>\n"
        "На сайте: «Резюме» → «Шаблон» → «Применить»\n\n"
        "<b>Доступно 8 шаблонов:</b>\n"
        "• Минималистичный — IT, стартапы\n"
        "• Классический — финансы, юриспруденция\n"
        "• ATS-оптимизированный — hh.ru, SuperJob ⭐\n"
        "• Международный — работа за рубежом\n"
        "• И ещё 4 варианта"
    ),
    "kb:plans": (
        "💳 <b>Тарифные планы</b>",
        "<b>FREE</b> — бесплатно: 1 резюме, 3 авто-отклика/день\n"
        "<b>СТАРТ — 990 ₽/мес:</b> 10 резюме, 50 откликов/день\n"
        "<b>ПРО — 2 490 ₽/мес:</b> безлимит резюме, 200 откликов/день\n"
        "<b>БЕЗЛИМИТ — 4 990 ₽/мес:</b> 9 999 откликов, API\n\n"
        "Оплата: крипто, карты РФ, Revolut\n"
        "Оформить: /pay"
    ),
    "kb:cancel": (
        "❌ <b>Отмена подписки</b>",
        "В боте: /cancel → «Подписка» → «Отменить»\n"
        "На сайте: «Биллинг» → «Отменить подписку»\n\n"
        "Доступ сохраняется до конца периода. Данные не удаляются.\n\n"
        "Если кнопки не работают или нужен возврат средств — "
        "напишите @maksimabramov, разберёмся в течение часа 🕐"
    ),
}

def _help_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Скачать PDF", callback_data="kb:pdf"),
         InlineKeyboardButton(text="🎨 Форматирование", callback_data="kb:format")],
        [InlineKeyboardButton(text="🖼 Шаблоны", callback_data="kb:templates"),
         InlineKeyboardButton(text="💳 Тарифы", callback_data="kb:plans")],
        [InlineKeyboardButton(text="❌ Отмена подписки", callback_data="kb:cancel")],
        [InlineKeyboardButton(text="✉️ Написать в поддержку", callback_data="support")],
    ])


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>База знаний ResumeAI</b>\n\n"
        "Выберите тему или напишите свой вопрос — "
        "отвечаем <b>в течение часа</b> 🕐",
        reply_markup=_help_kb(),
    )


@router.callback_query(F.data.startswith("kb:"))
async def kb_article(callback: CallbackQuery):
    await callback.answer()
    title, body = _KB_ARTICLES.get(callback.data, ("❓", "Статья не найдена"))
    await callback.message.answer(
        f"{title}\n\n{body}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="« Назад к помощи", callback_data="kb:menu")],
        ]),
    )


@router.callback_query(F.data == "kb:menu")
async def kb_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "❓ <b>База знаний ResumeAI</b>\n\n"
        "Выберите тему или напишите свой вопрос — "
        "отвечаем <b>в течение часа</b> 🕐",
        reply_markup=_help_kb(),
    )




class SupportStates(StatesGroup):
    waiting_message = State()


# ── Open support ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "support")
async def open_support(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_message)
    await callback.message.edit_text(SUPPORT_MESSAGE, reply_markup=support_kb())


# ── Receive support message (also handles admin replies — same state, merged) ──

@router.message(SupportStates.waiting_message, F.text)
async def got_support_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    reply_user_id = data.get("reply_to_user_id")

    await state.clear()

    # ── Admin is replying to a user ───────────────────────────────────────────
    if reply_user_id:
        try:
            await bot.send_message(
                reply_user_id,
                f"💬 <b>Ответ поддержки:</b>\n\n{message.text}",
            )
            await message.answer("✅ Ответ отправлен пользователю.")
        except Exception as e:
            await message.answer(f"⚠️ Не удалось отправить: {e}")
        return

    # ── Regular user support message → forward to admin ──────────────────────
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _reply_kb(user_id: int):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="↩️ Ответить пользователю",
            callback_data=f"reply_user:{user_id}",
        )],
    ])
