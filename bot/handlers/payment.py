"""
Payment handler — three methods:
  💎 Crypto   — CryptoBot auto invoice
  🇷🇺 RU Card  — manual, admin approval
  💳 Revolut  — manual, admin approval
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_or_create_user, save_user, save_payment, update_payment_status
from config import PRICING, ADMIN_ID, CRYPTOBOT_TOKEN, RU_CARD_NUMBER, RU_CARD_HOLDER, RU_BANK_NAME, REVOLUT_TAG, REVOLUT_LINK
from utils.keyboards import (
    buy_credits_kb, buy_assistant_kb, main_menu_kb,
    payment_method_kb, manual_paid_kb, admin_approve_kb, crypto_check_kb,
)
from utils.texts import (
    BUY_MESSAGE, PAYMENT_SUCCESS,
    PAYMENT_CRYPTO_PENDING, PAYMENT_CRYPTO_CHECKING,
    PAYMENT_MANUAL_RU, PAYMENT_MANUAL_REVOLUT,
    PAYMENT_RECEIPT_ASK, PAYMENT_RECEIPT_SENT,
    PAYMENT_RECEIPT_CHECKING, PAYMENT_AUTO_APPROVED,
    PAYMENT_CHECK_PENDING, PAYMENT_NOT_FOUND,
    ADMIN_PAYMENT_NOTIFY, ADMIN_PAYMENT_AI_ANALYSIS,
    ADMIN_PAYMENT_APPROVED, ADMIN_PAYMENT_REJECTED,
    PAYMENT_APPROVED_USER, PAYMENT_REJECTED_USER,
)

router = Router()

PACKAGE_CALLBACKS = {
    "buy_basic": "basic",
    "buy_pro": "pro",
    "buy_vip": "vip",
    "buy_assistant_50": "assistant_50",
    "buy_assistant_200": "assistant_200",
    "buy_assistant_unlimited": "assistant_unlimited",
}


class PaymentStates(StatesGroup):
    waiting_receipt = State()   # waiting for screenshot from user (manual payment)


# ---------------------------------------------------------------------------
# Buy menu
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "buy_credits")
async def show_buy_menu(callback: CallbackQuery):
    await callback.message.edit_text(BUY_MESSAGE, reply_markup=buy_credits_kb())


# ---------------------------------------------------------------------------
# Step 1 — package selected → choose payment method
# ---------------------------------------------------------------------------

@router.callback_query(F.data.in_(set(PACKAGE_CALLBACKS.keys())))
async def select_payment_method(callback: CallbackQuery):
    package_key = PACKAGE_CALLBACKS[callback.data]
    pkg = PRICING[package_key]
    text = (
        f"Выбран пакет: <b>{pkg['name']}</b>\n"
        f"Сумма: <b>{pkg['price_rub']}₽</b> / <b>{pkg['price_usdt']} USDT</b>\n\n"
        "Выбери способ оплаты:"
    )
    await callback.message.edit_text(text, reply_markup=payment_method_kb(package_key))


# ---------------------------------------------------------------------------
# Step 2a — Crypto (CryptoBot)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("pay_method:") & F.data.endswith(":crypto"))
async def pay_crypto(callback: CallbackQuery):
    package_key = callback.data.split(":")[1]

    if not CRYPTOBOT_TOKEN:
        await callback.answer("Криптооплата временно недоступна.", show_alert=True)
        return

    pkg = PRICING[package_key]
    await callback.message.edit_text("⏳ Создаю инвойс...")

    try:
        from services.payment_service import create_crypto_invoice
        pay_url, invoice_id = await create_crypto_invoice(callback.from_user.id, package_key)

        await save_payment(
            telegram_id=callback.from_user.id,
            amount_rub=pkg["price_rub"],
            package=package_key,
            payment_id=invoice_id,
        )

        await callback.message.edit_text(
            PAYMENT_CRYPTO_PENDING.format(
                usdt=pkg["price_usdt"],
                url=pay_url,
            ),
            reply_markup=crypto_check_kb(invoice_id, package_key),
        )
    except Exception as e:
        await callback.message.edit_text(
            f"⚠️ Ошибка при создании инвойса: {e}",
            reply_markup=main_menu_kb(),
        )


@router.callback_query(F.data.startswith("check_crypto:"))
async def check_crypto(callback: CallbackQuery):
    _, invoice_id, package_key = callback.data.split(":", 2)

    # Answer callback ONCE immediately — removes Telegram's loading spinner
    await callback.answer()

    try:
        from services.payment_service import check_crypto_invoice, apply_package_credits
        status = await check_crypto_invoice(invoice_id)

        if status == "paid":
            pkg = PRICING[package_key]
            await apply_package_credits(callback.from_user.id, package_key)
            await update_payment_status(invoice_id, "succeeded")
            await callback.message.edit_text(
                PAYMENT_SUCCESS.format(name=pkg["name"]),
                reply_markup=main_menu_kb(),
            )
        elif status == "expired":
            await callback.message.edit_text(
                "❌ Инвойс истёк. Создай новый:",
                reply_markup=buy_credits_kb(),
            )
        else:
            # Not paid yet — edit message so user sees clear feedback
            await callback.message.edit_text(
                PAYMENT_CHECK_PENDING,
                reply_markup=crypto_check_kb(invoice_id, package_key),
            )

    except Exception as e:
        await callback.message.edit_text(
            f"⚠️ Ошибка при проверке: {e}\n\nПопробуй ещё раз.",
            reply_markup=crypto_check_kb(invoice_id, package_key),
        )


# ---------------------------------------------------------------------------
# Step 2b — Manual: RU Card
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("pay_method:") & F.data.endswith(":rucard"))
async def pay_rucard(callback: CallbackQuery, state: FSMContext):
    package_key = callback.data.split(":")[1]
    pkg = PRICING[package_key]

    db_payment = await save_payment(
        telegram_id=callback.from_user.id,
        amount_rub=pkg["price_rub"],
        package=package_key,
    )

    await state.set_state(PaymentStates.waiting_receipt)
    await state.update_data(payment_db_id=db_payment.id, package_key=package_key, payment_method="rucard")

    text = PAYMENT_MANUAL_RU.format(
        amount=pkg["price_rub"],
        card=RU_CARD_NUMBER,
        holder=RU_CARD_HOLDER,
        bank=RU_BANK_NAME,
    )
    await callback.message.edit_text(text, reply_markup=manual_paid_kb(db_payment.id))


# ---------------------------------------------------------------------------
# Step 2c — Manual: Revolut
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("pay_method:") & F.data.endswith(":revolut"))
async def pay_revolut(callback: CallbackQuery, state: FSMContext):
    package_key = callback.data.split(":")[1]
    pkg = PRICING[package_key]

    db_payment = await save_payment(
        telegram_id=callback.from_user.id,
        amount_rub=pkg["price_rub"],
        package=package_key,
    )

    await state.set_state(PaymentStates.waiting_receipt)
    await state.update_data(payment_db_id=db_payment.id, package_key=package_key, payment_method="revolut")

    revolut_ref = REVOLUT_LINK or REVOLUT_TAG
    text = PAYMENT_MANUAL_REVOLUT.format(
        amount_rub=pkg["price_rub"],
        amount_usdt=pkg["price_usdt"],
        revolut=revolut_ref,
    )
    await callback.message.edit_text(text, reply_markup=manual_paid_kb(db_payment.id))


# ---------------------------------------------------------------------------
# Step 3 — User clicks "Я оплатил" → ask for receipt screenshot
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("manual_paid:"))
async def ask_for_receipt(callback: CallbackQuery, state: FSMContext):
    payment_db_id = int(callback.data.split(":")[1])

    # If state was lost (e.g. bot restart), restore from callback
    data = await state.get_data()
    if not data.get("payment_db_id"):
        await state.set_state(PaymentStates.waiting_receipt)
        await state.update_data(payment_db_id=payment_db_id, package_key="unknown")

    await callback.message.edit_text(PAYMENT_RECEIPT_ASK)


# ---------------------------------------------------------------------------
# Step 4 — User sends screenshot → AI check → auto-approve or → admin
# ---------------------------------------------------------------------------

@router.message(PaymentStates.waiting_receipt, F.photo)
async def got_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    payment_db_id = data.get("payment_db_id", 0)
    package_key   = data.get("package_key", "unknown")
    payment_method = data.get("payment_method", "rucard")   # "rucard" | "revolut"

    await state.clear()

    pkg  = PRICING.get(package_key, {})
    file_id = message.photo[-1].file_id

    # Tell the user we're checking
    checking_msg = await message.answer(PAYMENT_RECEIPT_CHECKING)

    # ── Mark payment as awaiting_review in DB ─────────────────────────────
    from database.db import get_session
    from models.user import Payment
    from sqlalchemy import select
    async with get_session() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_db_id))
        payment_row = result.scalar_one_or_none()
        if payment_row:
            payment_row.status = "awaiting_review"

    # ── AI receipt analysis ───────────────────────────────────────────────
    try:
        from services.receipt_checker import check_receipt
        ai_result = await check_receipt(
            file_id=file_id,
            expected_amount_rub=pkg.get("price_rub", 0),
            payment_method=payment_method,
            card_number=RU_CARD_NUMBER,
            revolut_tag=REVOLUT_TAG,
        )
    except Exception as e:
        from services.receipt_checker import ReceiptResult
        ai_result = ReceiptResult(
            verdict="manual", confidence=0.0,
            reason=f"Ошибка AI: {e}",
            analysis="AI-проверка не удалась.",
        )

    # ── AUTO-APPROVE ──────────────────────────────────────────────────────
    if ai_result.verdict == "approve":
        try:
            from services.payment_service import apply_package_credits
            await apply_package_credits(message.from_user.id, package_key)
            await update_payment_status_by_id(payment_db_id, "succeeded")

            await checking_msg.delete()
            await message.answer(
                PAYMENT_AUTO_APPROVED.format(name=pkg.get("name", package_key)),
                reply_markup=main_menu_kb(),
            )

            # Notify admin about auto-approval (FYI, no action needed)
            admin_caption = (
                ADMIN_PAYMENT_NOTIFY.format(
                    user_id=message.from_user.id,
                    username=message.from_user.username or "—",
                    full_name=message.from_user.full_name or "—",
                    package=pkg.get("name", package_key),
                    amount=pkg.get("price_rub", "?"),
                    payment_db_id=payment_db_id,
                )
                + "\n\n✅ <b>Подтверждено автоматически AI</b>"
                + ADMIN_PAYMENT_AI_ANALYSIS.format(
                    verdict_emoji="✅",
                    reason=ai_result.reason,
                    confidence=f"{ai_result.confidence:.0%}",
                    analysis=ai_result.analysis,
                )
            )
            try:
                await bot.send_photo(
                    ADMIN_ID,
                    photo=file_id,
                    caption=admin_caption[:1020],   # Telegram caption limit
                )
            except Exception:
                pass
        except Exception as e:
            await checking_msg.delete()
            await message.answer(f"⚠️ Ошибка начисления: {e}", reply_markup=main_menu_kb())
        return

    # ── MANUAL REVIEW → forward to admin ─────────────────────────────────
    verdict_emoji = "⚠️" if ai_result.confidence < 0.4 else "🤔"

    admin_caption = (
        ADMIN_PAYMENT_NOTIFY.format(
            user_id=message.from_user.id,
            username=message.from_user.username or "—",
            full_name=message.from_user.full_name or "—",
            package=pkg.get("name", package_key),
            amount=pkg.get("price_rub", "?"),
            payment_db_id=payment_db_id,
        )
        + ADMIN_PAYMENT_AI_ANALYSIS.format(
            verdict_emoji=verdict_emoji,
            reason=ai_result.reason,
            confidence=f"{ai_result.confidence:.0%}",
            analysis=ai_result.analysis,
        )
    )

    try:
        await bot.send_photo(
            ADMIN_ID,
            photo=file_id,
            caption=admin_caption[:1020],
            reply_markup=admin_approve_kb(payment_db_id, message.from_user.id, package_key),
        )
    except Exception:
        pass

    await checking_msg.delete()
    await message.answer(PAYMENT_RECEIPT_SENT, reply_markup=main_menu_kb())


@router.message(PaymentStates.waiting_receipt)
async def receipt_not_photo(message: Message):
    await message.answer("📸 Пожалуйста, отправь скриншот оплаты как <b>фото</b>.")


# ---------------------------------------------------------------------------
# Admin: approve / reject
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("admin_ok:"))
async def admin_approve(callback: CallbackQuery, bot: Bot):
    _, payment_db_id_str, telegram_id_str, package_key = callback.data.split(":", 3)
    payment_db_id = int(payment_db_id_str)
    telegram_id = int(telegram_id_str)

    try:
        from services.payment_service import apply_package_credits
        await apply_package_credits(telegram_id, package_key)
        await update_payment_status_by_id(payment_db_id, "succeeded")

        pkg = PRICING[package_key]

        # Notify user
        try:
            await bot.send_message(
                telegram_id,
                PAYMENT_APPROVED_USER.format(name=pkg["name"]),
                reply_markup=main_menu_kb(),
            )
        except Exception:
            pass

        await callback.message.edit_caption(
            caption=callback.message.caption + "\n\n" + ADMIN_PAYMENT_APPROVED,
        )
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("admin_no:"))
async def admin_reject(callback: CallbackQuery, bot: Bot):
    _, payment_db_id_str, telegram_id_str, package_key = callback.data.split(":", 3)
    payment_db_id = int(payment_db_id_str)
    telegram_id = int(telegram_id_str)

    await update_payment_status_by_id(payment_db_id, "failed")

    try:
        await bot.send_message(telegram_id, PAYMENT_REJECTED_USER)
    except Exception:
        pass

    await callback.message.edit_caption(
        caption=callback.message.caption + "\n\n" + ADMIN_PAYMENT_REJECTED,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def update_payment_status_by_id(payment_db_id: int, status: str):
    from database.db import get_session
    from models.user import Payment
    from sqlalchemy import select
    async with get_session() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_db_id))
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = status
