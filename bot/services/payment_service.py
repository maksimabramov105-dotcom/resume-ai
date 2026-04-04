"""
Payment service supporting three methods:
  1. CryptoBot — automatic crypto payments via @CryptoBot API (USDT/TON/BTC etc.)
  2. RU Card    — manual transfer to Russian bank card, admin approval
  3. Revolut    — manual transfer to Revolut, admin approval
"""
from config import PRICING, CRYPTOBOT_TOKEN


# ---------------------------------------------------------------------------
# CryptoBot
# ---------------------------------------------------------------------------

async def create_crypto_invoice(telegram_id: int, package: str) -> tuple[str, str]:
    """
    Create CryptoBot invoice.
    Returns (pay_url, invoice_id_as_str).
    Requires: pip install aiocryptopay
    Get token: @CryptoBot → /pay → Create App
    """
    from aiocryptopay import AioCryptoPay, Networks

    crypto = AioCryptoPay(token=CRYPTOBOT_TOKEN, network=Networks.MAIN_NET)

    pkg = PRICING[package]
    price_usdt = pkg.get("price_usdt", 1.00)

    invoice = await crypto.create_invoice(
        asset="USDT",
        amount=price_usdt,
        description=f"РезюмеАИ: {pkg['name']}",
        payload=f"{telegram_id}:{package}",
        expires_in=3600,  # 1 hour
    )
    await crypto.close()

    return invoice.bot_invoice_url, str(invoice.invoice_id)


async def check_crypto_invoice(invoice_id: str) -> str:
    """
    Check CryptoBot invoice status.
    Returns: 'paid' | 'active' | 'expired'
    """
    from aiocryptopay import AioCryptoPay, Networks

    crypto = AioCryptoPay(token=CRYPTOBOT_TOKEN, network=Networks.MAIN_NET)
    invoices = await crypto.get_invoices(invoice_ids=[int(invoice_id)])
    await crypto.close()

    if not invoices:
        return "expired"
    return invoices[0].status  # 'active', 'paid', 'expired'


# ---------------------------------------------------------------------------
# Credits helper (shared between all payment methods)
# ---------------------------------------------------------------------------

async def apply_package_credits(telegram_id: int, package: str):
    """Add credits to user after successful payment."""
    from database.db import get_or_create_user, save_user
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
