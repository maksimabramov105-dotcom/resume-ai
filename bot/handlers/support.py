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
from utils.texts import ADMIN_SUPPORT_NOTIFY   # admin-only, always Russian
from utils.bot_translations import t
from database.db import get_or_create_user

router = Router()

# ── Knowledge base ────────────────────────────────────────────────────────────

_KB_ARTICLES_RU = {
    "kb:pdf": (
        "📄 <b>Как скачать резюме в PDF</b>",
        "1. Создайте резюме через /resume\n"
        "2. Нажмите кнопку <b>«📄 Скачать PDF»</b> — файл придёт в чат\n"
        "3. На сайте: кнопка <b>«Экспорт PDF»</b> в правом верхнем углу\n\n"
        "<b>PDF не скачивается?</b> Обновите страницу или напишите нам — "
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
        "• ATS-оптимизированный — LinkedIn, Indeed ⭐\n"
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
        "Если нужен возврат средств — напишите в поддержку, разберёмся в течение часа 🕐"
    ),
}

_KB_ARTICLES_EN = {
    "kb:pdf": (
        "📄 <b>How to download your resume as PDF</b>",
        "1. Generate your resume via /resume\n"
        "2. Click <b>«📄 Download PDF»</b> — the file will arrive in this chat\n"
        "3. On the website: click <b>«Export PDF»</b> in the top-right corner\n\n"
        "<b>PDF not downloading?</b> Refresh the page or contact us — "
        "we reply within an hour 🕐"
    ),
    "kb:format": (
        "🎨 <b>Formatting looks wrong</b>",
        "Common causes:\n"
        "• <b>Text too long</b> — trim to 1-2 pages\n"
        "• <b>Too many symbols</b> •→★ — replace with dashes and numbers\n"
        "• <b>Wrong template</b> — try «Classic» or «ATS-optimized»\n\n"
        "Click <b>«Regenerate»</b> in the editor — AI will rebuild with clean structure."
    ),
    "kb:templates": (
        "🖼 <b>How to change the resume template</b>",
        "In the bot: /resume → <b>«Change Template»</b>\n"
        "On the website: «Resume» → «Template» → «Apply»\n\n"
        "<b>8 templates available:</b>\n"
        "• Minimalist — tech, startups\n"
        "• Classic — finance, legal\n"
        "• ATS-optimized — job boards ⭐\n"
        "• International — overseas jobs\n"
        "• And 4 more"
    ),
    "kb:plans": (
        "💳 <b>Pricing plans</b>",
        "<b>FREE</b> — free: 1 resume, 3 auto-applies/day\n"
        "<b>STARTER — 990₽/mo:</b> 10 resumes, 50 applies/day\n"
        "<b>PRO — 2,490₽/mo:</b> unlimited resumes, 200 applies/day\n"
        "<b>UNLIMITED — 4,990₽/mo:</b> 9,999 applies, API access\n\n"
        "Payment: crypto, Russian card, Revolut\n"
        "Subscribe: /pay"
    ),
    "kb:cancel": (
        "❌ <b>Cancel subscription</b>",
        "In the bot: /cancel → «Subscription» → «Cancel»\n"
        "On the website: «Billing» → «Cancel Subscription»\n\n"
        "Access continues until the end of the paid period. Your data is not deleted.\n\n"
        "Need a refund? Contact support — we'll sort it within an hour 🕐"
    ),
}


def _help_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    if lang == 'en':
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 Download PDF",    callback_data="kb:pdf"),
             InlineKeyboardButton(text="🎨 Formatting",      callback_data="kb:format")],
            [InlineKeyboardButton(text="🖼 Templates",       callback_data="kb:templates"),
             InlineKeyboardButton(text="💳 Plans",           callback_data="kb:plans")],
            [InlineKeyboardButton(text="❌ Cancel plan",     callback_data="kb:cancel")],
            [InlineKeyboardButton(text="✉️ Contact Support", callback_data="support")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Скачать PDF",          callback_data="kb:pdf"),
         InlineKeyboardButton(text="🎨 Форматирование",       callback_data="kb:format")],
        [InlineKeyboardButton(text="🖼 Шаблоны",             callback_data="kb:templates"),
         InlineKeyboardButton(text="💳 Тарифы",              callback_data="kb:plans")],
        [InlineKeyboardButton(text="❌ Отмена подписки",      callback_data="kb:cancel")],
        [InlineKeyboardButton(text="✉️ Написать в поддержку", callback_data="support")],
    ])


def _back_kb(lang: str = 'ru') -> InlineKeyboardMarkup:
    label = "« Back to Help" if lang == 'en' else "« Назад к помощи"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data="kb:menu")],
    ])


@router.message(Command("help"))
async def cmd_help(message: Message):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'en'
    if lang == 'en':
        text = (
            "❓ <b>ResumeAI Help Center</b>\n\n"
            "Choose a topic or write your question — "
            "we reply <b>within an hour</b> 🕐"
        )
    else:
        text = (
            "❓ <b>База знаний ResumeAI</b>\n\n"
            "Выберите тему или напишите свой вопрос — "
            "отвечаем <b>в течение часа</b> 🕐"
        )
    await message.answer(text, reply_markup=_help_kb(lang))


@router.callback_query(F.data.startswith("kb:") & ~F.data.in_({"kb:menu"}))
async def kb_article(callback: CallbackQuery):
    await callback.answer()
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'en'
    articles = _KB_ARTICLES_EN if lang == 'en' else _KB_ARTICLES_RU
    title, body = articles.get(callback.data, ("❓", "Article not found" if lang == 'en' else "Статья не найдена"))
    await callback.message.answer(
        f"{title}\n\n{body}",
        reply_markup=_back_kb(lang),
    )


@router.callback_query(F.data == "kb:menu")
async def kb_menu(callback: CallbackQuery):
    await callback.answer()
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'en'
    if lang == 'en':
        text = (
            "❓ <b>ResumeAI Help Center</b>\n\n"
            "Choose a topic or write your question — "
            "we reply <b>within an hour</b> 🕐"
        )
    else:
        text = (
            "❓ <b>База знаний ResumeAI</b>\n\n"
            "Выберите тему или напишите свой вопрос — "
            "отвечаем <b>в течение часа</b> 🕐"
        )
    await callback.message.edit_text(text, reply_markup=_help_kb(lang))


class SupportStates(StatesGroup):
    waiting_message = State()


@router.callback_query(F.data == "support")
async def open_support(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'en'
    await state.set_state(SupportStates.waiting_message)
    await callback.message.edit_text(t(lang, 'support.ask'), reply_markup=support_kb(lang))


@router.message(SupportStates.waiting_message, F.text)
async def got_support_message(message: Message, state: FSMContext, bot: Bot):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'en'
    data = await state.get_data()
    reply_user_id = data.get("reply_to_user_id")
    await state.clear()

    if reply_user_id:
        try:
            await bot.send_message(reply_user_id, f"💬 <b>Ответ поддержки:</b>\n\n{message.text}")
            await message.answer("✅ Ответ отправлен пользователю.")
        except Exception as e:
            await message.answer(f"⚠️ Не удалось отправить: {e}")
        return

    notify = ADMIN_SUPPORT_NOTIFY.format(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name or "—",
        username=message.from_user.username or "—",
        text=message.text,
    )
    try:
        await bot.send_message(ADMIN_ID, notify, reply_markup=_reply_kb(message.from_user.id))
    except Exception:
        pass

    await message.answer(t(lang, 'support.sent'), reply_markup=main_menu_kb(lang))


@router.message(SupportStates.waiting_message, F.photo)
async def got_support_photo(message: Message, state: FSMContext, bot: Bot):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'en'
    await state.clear()

    caption_text = message.caption or ("(no caption)" if lang == 'en' else "(без подписи)")
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

    await message.answer(t(lang, 'support.sent'), reply_markup=main_menu_kb(lang))


@router.message(SupportStates.waiting_message)
async def support_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'support.wrong_type'))


@router.callback_query(F.data.startswith("reply_user:"))
async def admin_reply_prompt(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])
    await state.set_state(SupportStates.waiting_message)
    await state.update_data(reply_to_user_id=user_id)
    await callback.message.answer(f"✏️ Напиши ответ пользователю <code>{user_id}</code>:")
    await callback.answer()


def _reply_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="↩️ Ответить пользователю",
            callback_data=f"reply_user:{user_id}",
        )],
    ])
