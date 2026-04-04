from aiogram import Router, F
from aiogram.types import CallbackQuery

from database.db import get_or_create_user, save_user, save_payment, update_payment_status
from config import PRICING
from utils.keyboards import payment_check_kb, main_menu_kb, buy_credits_kb
from utils.texts import BUY_MESSAGE, PAYMENT_PENDING, PAYMENT_SUCCESS, PAYMENT_CHECK_PENDING, PAYMENT_NOT_FOUND

router = Router()

# Package key → callback prefix mapping
PACKAGE_CALLBACKS = {
    "buy_basic": "basic",
    "buy_pro": "pro",
    "buy_vip": "vip",
    "buy_assistant_50": "assistant_50",
    "buy_assistant_200": "assistant_200",
    "buy_assistant_unlimited": "assistant_unlimited",
}


@router.callback_query(F.data == "buy_credits")
async def show_buy_menu(callback: CallbackQuery):
    await callback.message.edit_text(BUY_MESSAGE, reply_markup=buy_credits_kb())


@router.callback_query(F.data.in_(set(PACKAGE_CALLBACKS.keys())))
async def initiate_payment(callback: CallbackQuery):
    package_key = PACKAGE_CALLBACKS[callback.data]
    pkg = PRICING[package_key]

    try:
        from services.payment_service import create_payment
        payment_url, payment_id = await create_payment(callback.from_user.id, package_key)

        await save_payment(
            telegram_id=callback.from_user.id,
            amount_rub=pkg["price_rub"],
            package=package_key,
            payment_id=payment_id,
        )

        await callback.message.edit_text(
            PAYMENT_PENDING.format(url=payment_url),
            reply_markup=payment_check_kb(payment_id),
        )
    except Exception as e:
        await callback.message.edit_text(
            f"⚠️ Ошибка при создании платежа: {e}\n\n"
            "Пожалуйста, свяжись с поддержкой.",
            reply_markup=main_menu_kb(),
        )


@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment(callback: CallbackQuery):
    payment_id = callback.data.split(":", 1)[1]

    try:
        from services.payment_service import get_payment_status
        status, package_key = await get_payment_status(payment_id)

        if status == "succeeded":
            pkg = PRICING[package_key]
            user = await get_or_create_user(callback.from_user.id)

            # Add credits
            for field in ("credits_resume", "credits_cover_letter", "credits_interview", "credits_assistant"):
                if field.replace("credits_", "") in pkg or field in pkg:
                    pass
            if "credits_resume" in pkg:
                user.credits_resume += pkg["credits_resume"]
            if "credits_cover_letter" in pkg:
                user.credits_cover_letter += pkg["credits_cover_letter"]
            if "credits_interview" in pkg:
                user.credits_interview += pkg["credits_interview"]
            if "credits_assistant" in pkg:
                user.credits_assistant += pkg["credits_assistant"]

            user.total_spent_rub += pkg["price_rub"]

            if "duration_days" in pkg:
                from datetime import datetime, timedelta
                user.subscription_type = package_key
                user.subscription_expires = datetime.utcnow() + timedelta(days=pkg["duration_days"])

            await save_user(user)
            await update_payment_status(payment_id, "succeeded")

            await callback.message.edit_text(
                PAYMENT_SUCCESS.format(name=pkg["name"]),
                reply_markup=main_menu_kb(),
            )
        elif status == "pending":
            await callback.answer(PAYMENT_CHECK_PENDING, show_alert=True)
        else:
            await callback.message.edit_text(PAYMENT_NOT_FOUND, reply_markup=main_menu_kb())

    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)
