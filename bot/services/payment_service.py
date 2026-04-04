import uuid
from config import PRICING, YUKASSA_SHOP_ID, YUKASSA_SECRET_KEY


async def create_payment(telegram_id: int, package: str) -> tuple[str, str]:
    """Create a payment and return (confirmation_url, payment_id)."""
    from yookassa import Configuration, Payment as YooPayment

    Configuration.account_id = YUKASSA_SHOP_ID
    Configuration.secret_key = YUKASSA_SECRET_KEY

    pkg = PRICING[package]
    price = pkg["price_rub"]

    payment = YooPayment.create(
        {
            "amount": {
                "value": f"{price:.2f}",
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/resumeai_bot",
            },
            "capture": True,
            "description": f"РезюмеАИ: {pkg['name']} — {pkg['description']}",
            "metadata": {
                "telegram_id": str(telegram_id),
                "package": package,
            },
        },
        str(uuid.uuid4()),
    )

    return payment.confirmation.confirmation_url, payment.id


async def get_payment_status(payment_id: str) -> tuple[str, str]:
    """Get payment status and package. Returns (status, package_key)."""
    from yookassa import Configuration, Payment as YooPayment

    Configuration.account_id = YUKASSA_SHOP_ID
    Configuration.secret_key = YUKASSA_SECRET_KEY

    payment = YooPayment.find_one(payment_id)
    package = payment.metadata.get("package", "") if payment.metadata else ""
    return payment.status, package


async def process_payment_webhook(payment_data: dict, bot):
    """Handle webhook from ЮKassa after successful payment."""
    if payment_data.get("event") != "payment.succeeded":
        return

    obj = payment_data.get("object", {})
    metadata = obj.get("metadata", {})
    telegram_id = int(metadata.get("telegram_id", 0))
    package = metadata.get("package", "")

    if not telegram_id or not package or package not in PRICING:
        return

    from database.db import get_or_create_user, save_user, update_payment_status
    pkg = PRICING[package]
    user = await get_or_create_user(telegram_id)

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
        user.subscription_type = package
        user.subscription_expires = datetime.utcnow() + timedelta(days=pkg["duration_days"])

    await save_user(user)
    await update_payment_status(obj.get("id", ""), "succeeded")

    try:
        await bot.send_message(
            telegram_id,
            f"✅ Оплата прошла! Пакет «{pkg['name']}» активирован.\n"
            f"Ваш баланс обновлён.",
        )
    except Exception:
        pass
