from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from database.db import get_or_create_user, save_user
from services.user_service import add_referral_bonus
from utils.keyboards import main_menu_kb
from utils.bot_translations import t

# Analytics tracker — project root (3 levels up from bot/handlers/start.py)
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from analytics_tracker import track_start, DB_PATH as _ANALYTICS_DB_PATH
from maintenance import is_maintenance, broadcast_maintenance_start, broadcast_maintenance_end
from daily_reporter import send_daily_report, ADMIN_CHAT_ID as _REPORTER_ADMIN_ID

router = Router()

ADMIN_ID = int(_os.getenv("ADMIN_ID", "0"))


def _language_kb() -> InlineKeyboardMarkup:
    """Inline keyboard for first-run language selection."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English",  callback_data="lang:en"),
        ]
    ])


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    args = message.text.split(maxsplit=1)[1] if " " in message.text else ""
    user = await get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    # Referral handling
    if args.startswith("ref_") and not user.referred_by:
        referral_code = args[4:]
        from sqlalchemy import select
        from database.db import get_session
        from models.user import User as UserModel
        async with get_session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.referral_code == referral_code)
            )
            referrer = result.scalar_one_or_none()
            if referrer and referrer.telegram_id != user.telegram_id:
                user.referred_by = referrer.telegram_id
                await save_user(user)
                await add_referral_bonus(referrer)

    # Track join source for analytics (never raises)
    await track_start(user.telegram_id, args, _ANALYTICS_DB_PATH)

    # PostHog analytics
    try:
        from datetime import datetime as _dt
        from bot.analytics import track as _ph_track, identify as _ph_identify
        _ph_identify(user.telegram_id, {
            'username': user.username,
            'first_seen': _dt.utcnow().isoformat(),
            'language': message.from_user.language_code or user.language or '',
        })
        _ph_track(user.telegram_id, 'bot_started', {'source': 'telegram', 'referral': args})
    except Exception:
        pass

    # First-time user: ask language before showing main menu
    if not user.language:
        await message.answer(
            t(None, 'start.choose_lang'),
            reply_markup=_language_kb(),
        )
        return

    lang = user.language or 'en'
    await message.answer(t(lang, 'start.welcome'), reply_markup=main_menu_kb(lang))


@router.callback_query(F.data == "main_menu")
async def go_main_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'en'
    await callback.message.edit_text(t(lang, 'start.welcome'), reply_markup=main_menu_kb(lang))


# ── Admin: maintenance broadcast commands ────────────────────────────────────

@router.message(Command("maintenance_on"))
async def cmd_maintenance_on(message: Message):
    """Admin only: broadcast maintenance message to all active users."""
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(t('ru', 'admin.maintenance_on'))
    await broadcast_maintenance_start(message.bot)


@router.message(Command("maintenance_off"))
async def cmd_maintenance_off(message: Message):
    """Admin only: broadcast recovery message to all active users."""
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(t('ru', 'admin.maintenance_off'))
    await broadcast_maintenance_end(message.bot)


@router.message(Command("report"))
@router.message(Command("отчет"))
async def cmd_report(message: Message):
    """Admin only: trigger daily report immediately (/report or /отчет)."""
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(t('ru', 'admin.report_generating'))
    try:
        class _ReplyBot:
            async def send_message(self, chat_id, text, **kw):
                await message.answer(text, **kw)

        await send_daily_report(_ReplyBot(), ADMIN_ID, _ANALYTICS_DB_PATH)
    except Exception as exc:
        await message.answer(t('ru', 'admin.report_error', error=exc))


# ── Upgrade / Pay commands ────────────────────────────────────────────────────

@router.message(Command("upgrade"))
@router.message(Command("pay"))
@router.message(Command("plans"))
async def cmd_upgrade(message: Message):
    """Show payment options — Stripe card or contact support."""
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'en'
    if lang == 'en':
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Pay by card (Visa/MC/Amex)", url="https://resumeai-bot.ru/app#plans")],
            [InlineKeyboardButton(text="💬 Contact support", url="https://t.me/topbestworkerbot")],
        ])
        text = (
            "💎 <b>Choose your plan:</b>\n\n"
            "💳 <b>Card</b> (Visa / Mastercard / Amex) — secure Stripe checkout\n"
            "💬 <b>Other payment methods</b> — contact us in Telegram\n\n"
            "Plan activates <b>instantly</b> after payment ✅"
        )
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить картой (Visa/MC/Amex)", url="https://resumeai-bot.ru/app#plans")],
            [InlineKeyboardButton(text="💬 Связаться с поддержкой", url="https://t.me/topbestworkerbot")],
        ])
        text = (
            "💎 <b>Выберите тариф:</b>\n\n"
            "💳 <b>Карта</b> (Visa / Mastercard / Amex) — безопасная оплата через Stripe\n"
            "💬 <b>Другие способы оплаты</b> — свяжитесь с нами в Telegram\n\n"
            "После оплаты план активируется <b>мгновенно</b> ✅"
        )
    try:
        from bot.analytics import track as _ph_track
        _ph_track(message.from_user.id, 'subscription_page_viewed', {})
    except Exception:
        pass
    await message.answer(text, reply_markup=kb)


# ── Tracker command ────────────────────────────────────────────────────────────

@router.message(Command("tracker"))
@router.message(Command("stats"))
async def cmd_tracker(message: Message):
    """Show user's application stats."""
    import sqlite3
    import os as _os
    db_path = _os.getenv("AUTOAPPLY_DB", "/opt/resumeaibot/autoapply.db")
    uid = message.from_user.id
    user = await get_or_create_user(uid)
    lang = user.language or 'en'
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT COUNT(*), SUM(CASE WHEN status='sent' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN status='viewed' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN status='interview' THEN 1 ELSE 0 END) "
            "FROM applications WHERE user_id=?",
            (uid,)
        ).fetchone()
        conn.close()
        total, sent, viewed, interview = row if row else (0, 0, 0, 0)
        total    = total    or 0
        sent     = sent     or 0
        viewed   = viewed   or 0
        interview = interview or 0
    except Exception:
        total = sent = viewed = interview = 0

    if lang == 'en':
        text = (
            f"📊 <b>Your application stats:</b>\n\n"
            f"📬 Total sent: <b>{total}</b>\n"
            f"👀 Viewed by recruiter: <b>{viewed}</b>\n"
            f"🎯 Interviews: <b>{interview}</b>\n\n"
            f"<i>Tip: apply more to get more responses!</i>"
        )
    else:
        text = (
            f"📊 <b>Ваша статистика откликов:</b>\n\n"
            f"📬 Всего отправлено: <b>{total}</b>\n"
            f"👀 Просмотрено рекрутером: <b>{viewed}</b>\n"
            f"🎯 Приглашений на интервью: <b>{interview}</b>\n\n"
            f"<i>Подсказка: больше откликов = больше ответов!</i>"
        )
    from utils.keyboards import main_menu_kb
    await message.answer(text, reply_markup=main_menu_kb(lang))
