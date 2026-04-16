from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.db import get_or_create_user
from utils.keyboards import profile_kb, main_menu_kb
from utils.bot_translations import t

router = Router()

_SUB_KEYS = {
    "free":               "profile.sub.free",
    "basic":              "profile.sub.basic",
    "pro":                "profile.sub.pro",
    "vip":                "profile.sub.vip",
    "assistant_unlimited":"profile.sub.assistant_unlimited",
}


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'

    sub_label = t(lang, _SUB_KEYS.get(user.subscription_type, 'profile.sub.free'))

    text = t(lang, 'profile.header').format(
        full_name=user.full_name or callback.from_user.full_name or "—",
        subscription_type=sub_label,
        credits_resume=user.credits_resume,
        credits_cover_letter=user.credits_cover_letter,
        credits_interview=user.credits_interview,
        credits_assistant=user.credits_assistant,
        total_resumes_generated=user.total_resumes_generated,
        total_assistant_messages=user.total_assistant_messages,
        total_spent_rub=int(user.total_spent_rub),
    )

    await callback.message.edit_text(text, reply_markup=profile_kb(lang))


@router.callback_query(F.data == "referral")
async def show_referral(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'

    bot_info = await callback.bot.get_me()

    from sqlalchemy import select, func
    from database.db import get_session
    from models.user import User as UserModel
    async with get_session() as session:
        result = await session.execute(
            select(func.count()).where(UserModel.referred_by == user.telegram_id)
        )
        referral_count = result.scalar() or 0

    text = t(lang, 'referral.header').format(
        bot_username=bot_info.username,
        referral_code=user.referral_code or "—",
        referral_count=referral_count,
    )

    await callback.message.edit_text(text, reply_markup=main_menu_kb(lang))
