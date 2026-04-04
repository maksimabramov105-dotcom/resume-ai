from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.db import get_or_create_user
from utils.keyboards import profile_kb
from utils.texts import PROFILE_MESSAGE, REFERRAL_MESSAGE

router = Router()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)

    sub_labels = {
        "free": "Бесплатный",
        "basic": "Базовый",
        "pro": "Про",
        "vip": "VIP",
        "assistant_unlimited": "AI Безлимит",
    }
    sub_type = sub_labels.get(user.subscription_type, user.subscription_type)

    text = PROFILE_MESSAGE.format(
        full_name=user.full_name or callback.from_user.full_name or "—",
        subscription_type=sub_type,
        credits_resume=user.credits_resume,
        credits_cover_letter=user.credits_cover_letter,
        credits_interview=user.credits_interview,
        credits_assistant=user.credits_assistant,
        total_resumes_generated=user.total_resumes_generated,
        total_assistant_messages=user.total_assistant_messages,
        total_spent_rub=int(user.total_spent_rub),
    )

    await callback.message.edit_text(text, reply_markup=profile_kb())


@router.callback_query(F.data == "referral")
async def show_referral(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)

    bot_info = await callback.bot.get_me()

    # Count referrals
    from sqlalchemy import select, func
    from database.db import get_session
    from models.user import User as UserModel
    async with get_session() as session:
        result = await session.execute(
            select(func.count()).where(UserModel.referred_by == user.telegram_id)
        )
        referral_count = result.scalar() or 0

    text = REFERRAL_MESSAGE.format(
        bot_username=bot_info.username,
        referral_code=user.referral_code or "—",
        referral_count=referral_count,
    )

    from utils.keyboards import main_menu_kb
    await callback.message.edit_text(text, reply_markup=main_menu_kb())
