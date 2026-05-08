"""
Payment service — international edition (May 2026).

Supports:
  1. Stripe Checkout — handled by autoapply FastAPI webhooks (not this module)
  2. Revolut         — manual admin approval

NOTE: CryptoBot (USDT) and RU bank card methods were removed in May 2026
as part of the international pivot.  apply_package_credits() remains as
the shared helper for crediting any payment method.
"""
from config import PRICING


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

    # Track USD spend; total_spent_rub field retained for DB compatibility
    user.total_spent_rub += pkg.get("price_usd", 0.0)

    if "duration_days" in pkg:
        from datetime import datetime, timedelta
        user.subscription_type = package
        user.subscription_expires = datetime.utcnow() + timedelta(days=pkg["duration_days"])

    await save_user(user)
