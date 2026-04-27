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
# Admin-only strings stay in Russian; user-facing strings use t()
from utils.texts import (
    ADMIN_PAYMENT_NOTIFY, ADMIN_PAYMENT_AI_ANALYSIS,
    ADMIN_PAYMENT_APPROVED, ADMIN_PAYMENT_REJECTED,
)
from utils.bot_translations import t

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
    waiting_receipt = State()


# ---------------------------------------------------------------------------
# Buy menu
# ---------------------------------------------------------------------------

@router.callback_query(F.data == "buy_credits")
async def show_buy_menu(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    try:
        from bot.analytics import track as _ph_track
        _ph_track(callback.from_user.id, 'subscription_page_viewed', {})
    except Exception:
        pass
    await callback.message.edit_text(t(lang, 'buy.header'), reply_markup=buy_credits_kb(lang))


# ---------------------------------------------------------------------------
# Step 1 — package selected → choose payment method
# ---------------------------------------------------------------------------

@router.callback_query(F.data.in_(set(PACKAGE_CALLBACKS.keys())))
async def select_payment_method(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    package_key = PACKAGE_CALLBACKS[callback.data]
    pkg = PRICING[package_key]
    if lang == 'en':
        text = (
            f"Selected package: <b>{pkg['name']}</b>\n"
            f"Amount: <b>{pkg['price_rub']}₽</b> / <b>{pkg['price_usdt']} USDT</b>\n\n"
            "Choose payment method:"
        )
    else:
        text = (
            f"Выбран пакет: <b>{pkg['name']}</b>\n"
            f"Сумма: <b>{pkg['price_rub']}₽</b> / <b>{pkg['price_usdt']} USDT</b>\n\n"
            "Выбери способ оплаты:"
        )
    await callback.message.edit_text(text, reply_markup=payment_method_kb(package_key, lang))


# ---------------------------------------------------------------------------
# Step 2a — Crypto (CryptoBot)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("pay_method:") & F.data.endswith(":crypto"))
async def pay_crypto(callback: CallbackQuery):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    package_key = callback.data.split(":")[1]

    if not CRYPTOBOT_TOKEN:
        await callback.answer(t(lang, 'pay.crypto_unavailable'), show_alert=True)
        return

    pkg = PRICING[package_key]
    await callback.message.edit_text(t(lang, 'pay.loading'))

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
            t(lang, 'pay.crypto_pending').format(
                usdt=pkg["price_usdt"],
                pay_url=pay_url,
            ),
            reply_markup=crypto_check_kb(invoice_id, package_key, lang),
        )
    except Exception as e:
        await callback.message.edit_text(
            t(lang, 'pay.error_grant', error=e),
            reply_markup=main_menu_kb(lang),
        )


@router.callback_query(F.data.startswith("check_crypto:"))
async def check_crypto(callback: CallbackQuery):
    _, invoice_id, package_key = callback.data.split(":", 2)
    await callback.answer()

    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'

    try:
        from services.payment_service import check_crypto_invoice, apply_package_credits
        status = await check_crypto_invoice(invoice_id)

        if status == "paid":
            pkg = PRICING[package_key]
            await apply_package_credits(callback.from_user.id, package_key)
            await update_payment_status(invoice_id, "succeeded")
            try:
                import sys, os as _os
                _ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
                if _ROOT not in sys.path:
                    sys.path.insert(0, _ROOT)
                from analytics_tracker import track_payment, DB_PATH as _ADB
                await track_payment(callback.from_user.id, pkg["price_rub"], "crypto", _ADB)
                from bot.utils.posthog_tracker import track as _ph_track
                _ph_track(callback.from_user.id, 'payment_completed', {'plan': package_key, 'method': 'crypto', 'price_rub': pkg["price_rub"]})
            except Exception:
                pass
            await callback.message.edit_text(
                t(lang, 'pay.success').format(name=pkg["name"]),
                reply_markup=main_menu_kb(lang),
            )
        elif status == "expired":
            await callback.message.edit_text(
                t(lang, 'pay.not_found'),
                reply_markup=buy_credits_kb(lang),
            )
        else:
            await callback.message.edit_text(
                t(lang, 'pay.check_pending'),
                reply_markup=crypto_check_kb(invoice_id, package_key, lang),
            )

    except Exception as e:
        await callback.message.edit_text(
            t(lang, 'pay.error_grant', error=e),
            reply_markup=crypto_check_kb(invoice_id, package_key, lang),
        )


# ---------------------------------------------------------------------------
# Step 2b — Manual: RU Card
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("pay_method:") & F.data.endswith(":rucard"))
async def pay_rucard(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    package_key = callback.data.split(":")[1]
    pkg = PRICING[package_key]

    db_payment = await save_payment(
        telegram_id=callback.from_user.id,
        amount_rub=pkg["price_rub"],
        package=package_key,
    )

    await state.set_state(PaymentStates.waiting_receipt)
    await state.update_data(payment_db_id=db_payment.id, package_key=package_key, payment_method="rucard")

    text = t(lang, 'pay.manual_ru').format(
        amount=pkg["price_rub"],
        card=RU_CARD_NUMBER,
        holder=RU_CARD_HOLDER,
        bank=RU_BANK_NAME,
    )
    await callback.message.edit_text(text, reply_markup=manual_paid_kb(db_payment.id, lang))


# ---------------------------------------------------------------------------
# Step 2c — Manual: Revolut
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("pay_method:") & F.data.endswith(":revolut"))
async def pay_revolut(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
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
    text = t(lang, 'pay.manual_revolut').format(
        amount_rub=pkg["price_rub"],
        amount_usdt=pkg["price_usdt"],
        revolut=revolut_ref,
    )
    await callback.message.edit_text(text, reply_markup=manual_paid_kb(db_payment.id, lang))


# ---------------------------------------------------------------------------
# Step 3 — User clicks "Я оплатил" → ask for receipt screenshot
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("manual_paid:"))
async def ask_for_receipt(callback: CallbackQuery, state: FSMContext):
    payment_db_id = int(callback.data.split(":")[1])
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'

    data = await state.get_data()
    if not data.get("payment_db_id"):
        await state.set_state(PaymentStates.waiting_receipt)
        await state.update_data(payment_db_id=payment_db_id, package_key="unknown")

    await callback.message.edit_text(t(lang, 'pay.receipt_ask'))


# ---------------------------------------------------------------------------
# Step 4 — User sends screenshot → AI check → auto-approve or → admin
# ---------------------------------------------------------------------------

@router.message(PaymentStates.waiting_receipt, F.photo)
async def got_receipt(message: Message, state: FSMContext, bot: Bot):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'ru'

    data = await state.get_data()
    payment_db_id  = data.get("payment_db_id", 0)
    package_key    = data.get("package_key", "unknown")
    payment_method = data.get("payment_method", "rucard")

    await state.clear()

    pkg     = PRICING.get(package_key, {})
    file_id = message.photo[-1].file_id

    checking_msg = await message.answer(t(lang, 'pay.receipt_checking'))

    from database.db import get_session
    from models.user import Payment
    from sqlalchemy import select
    async with get_session() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_db_id))
        payment_row = result.scalar_one_or_none()
        if payment_row:
            payment_row.status = "awaiting_review"

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

    if ai_result.verdict == "approve":
        try:
            from services.payment_service import apply_package_credits
            await apply_package_credits(message.from_user.id, package_key)
            await _update_payment_status_by_id(payment_db_id, "succeeded")
            try:
                import sys, os as _os
                _ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
                if _ROOT not in sys.path:
                    sys.path.insert(0, _ROOT)
                from analytics_tracker import track_payment, DB_PATH as _ADB
                _method = "revolut" if payment_method == "revolut" else "card"
                await track_payment(message.from_user.id, pkg.get("price_rub", 0), _method, _ADB)
            except Exception:
                pass

            await checking_msg.delete()
            await message.answer(
                t(lang, 'pay.auto_approved').format(name=pkg.get("name", package_key)),
                reply_markup=main_menu_kb(lang),
            )

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
                await bot.send_photo(ADMIN_ID, photo=file_id, caption=admin_caption[:1020])
            except Exception:
                pass
        except Exception as e:
            await checking_msg.delete()
            await message.answer(t(lang, 'pay.error_grant', error=e), reply_markup=main_menu_kb(lang))
        return

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
            ADMIN_ID, photo=file_id, caption=admin_caption[:1020],
            reply_markup=admin_approve_kb(payment_db_id, message.from_user.id, package_key),
        )
    except Exception:
        pass

    await checking_msg.delete()
    await message.answer(t(lang, 'pay.receipt_sent'), reply_markup=main_menu_kb(lang))


@router.message(PaymentStates.waiting_receipt)
async def receipt_not_photo(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'pay.receipt_wrong_type'))


# ---------------------------------------------------------------------------
# Admin: approve / reject  (admin always gets Russian)
# ---------------------------------------------------------------------------

@router.callback_query(F.data.startswith("admin_ok:"))
async def admin_approve(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    _, payment_db_id_str, telegram_id_str, package_key = callback.data.split(":", 3)
    payment_db_id = int(payment_db_id_str)
    telegram_id   = int(telegram_id_str)

    try:
        from services.payment_service import apply_package_credits
        await apply_package_credits(telegram_id, package_key)
        await _update_payment_status_by_id(payment_db_id, "succeeded")
        try:
            import sys, os as _os
            _ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
            if _ROOT not in sys.path:
                sys.path.insert(0, _ROOT)
            from analytics_tracker import track_payment, DB_PATH as _ADB
            _pkg_info = PRICING.get(package_key, {"price_rub": 0})
            await track_payment(telegram_id, _pkg_info.get("price_rub", 0), "card", _ADB)
        except Exception:
            pass

        pkg = PRICING.get(package_key, {"name": package_key})

        # Notify the user in THEIR language
        from database.db import get_user
        target_user = await get_user(telegram_id)
        target_lang = (target_user.language if target_user else None) or 'ru'
        try:
            await bot.send_message(
                telegram_id,
                t(target_lang, 'pay.approved_user').format(name=pkg["name"]),
                reply_markup=main_menu_kb(target_lang),
            )
        except Exception:
            pass

        new_caption = ((callback.message.caption or "") + "\n\n" + ADMIN_PAYMENT_APPROVED)[:1020]
        await callback.message.edit_caption(caption=new_caption)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("admin_no:"))
async def admin_reject(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    _, payment_db_id_str, telegram_id_str, package_key = callback.data.split(":", 3)
    payment_db_id = int(payment_db_id_str)
    telegram_id   = int(telegram_id_str)

    await _update_payment_status_by_id(payment_db_id, "failed")

    from database.db import get_user
    target_user = await get_user(telegram_id)
    target_lang = (target_user.language if target_user else None) or 'ru'
    try:
        await bot.send_message(telegram_id, t(target_lang, 'pay.rejected_user'))
    except Exception:
        pass

    new_caption = ((callback.message.caption or "") + "\n\n" + ADMIN_PAYMENT_REJECTED)[:1020]
    await callback.message.edit_caption(caption=new_caption)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _update_payment_status_by_id(payment_db_id: int, status: str):
    from database.db import get_session
    from models.user import Payment
    from sqlalchemy import select
    async with get_session() as session:
        result = await session.execute(select(Payment).where(Payment.id == payment_db_id))
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = status
