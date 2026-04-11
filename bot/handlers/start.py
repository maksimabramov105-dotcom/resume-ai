from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command

from database.db import get_or_create_user, save_user
from services.user_service import add_referral_bonus
from utils.keyboards import main_menu_kb
from utils.texts import START_MESSAGE

# Analytics tracker — project root (3 levels up from bot/handlers/start.py)
# track_start is wrapped in try/except inside analytics_tracker so it never crashes
import sys, os as _os
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from analytics_tracker import track_start, DB_PATH as _ANALYTICS_DB_PATH
from maintenance import is_maintenance, broadcast_maintenance_start, broadcast_maintenance_end
from daily_reporter import send_daily_report, ADMIN_CHAT_ID as _REPORTER_ADMIN_ID

router = Router()

ADMIN_ID = int(_os.getenv("ADMIN_ID", "6246429438"))


@router.message(CommandStart())
async def cmd_start(message: Message):
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
            from sqlalchemy import select
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

    await message.answer(START_MESSAGE, reply_markup=main_menu_kb())


@router.callback_query(F.data == "main_menu")
async def go_main_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(START_MESSAGE, reply_markup=main_menu_kb())


# ── Admin: maintenance broadcast commands ────────────────────────────────────

@router.message(Command("maintenance_on"))
async def cmd_maintenance_on(message: Message):
    """Admin only: broadcast maintenance message to all active users."""
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📢 Sending maintenance notification to all users…")
    await broadcast_maintenance_start(message.bot)


@router.message(Command("maintenance_off"))
async def cmd_maintenance_off(message: Message):
    """Admin only: broadcast recovery message to all active users."""
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("✅ Sending recovery notification to all users…")
    await broadcast_maintenance_end(message.bot)


@router.message(Command("report"))
async def cmd_report(message: Message):
    """Admin only: trigger daily report immediately."""
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("📊 Генерирую отчёт…")
    try:
        await send_daily_report(message.bot, ADMIN_ID, _ANALYTICS_DB_PATH)
    except Exception as exc:
        await message.answer(f"❌ Ошибка отчёта: {exc}")
