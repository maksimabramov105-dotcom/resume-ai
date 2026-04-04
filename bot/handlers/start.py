from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from database.db import get_or_create_user, save_user
from services.user_service import add_referral_bonus
from utils.keyboards import main_menu_kb
from utils.texts import START_MESSAGE

router = Router()


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

    await message.answer(START_MESSAGE, reply_markup=main_menu_kb())


@router.callback_query(F.data == "main_menu")
async def go_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(START_MESSAGE, reply_markup=main_menu_kb())
