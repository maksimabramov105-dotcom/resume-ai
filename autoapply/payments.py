"""
payments.py — Stripe payment integration for AutoApply.
CryptoBot was removed in the 2026-05 international pivot.
"""
import json
import logging
import os

import aiohttp

from autoapply.config import (
    AUTOAPPLY_DB,
    PLANS,
    BOT_TOKEN,
    ADMIN_CHAT_ID,
    WEBAPP_BASE_URL,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)

logger = logging.getLogger(__name__)

# Telegram API base URL — resolved at import time so BOT_TOKEN env var is read correctly
_TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ── Stripe Checkout ───────────────────────────────────────────────────────────

async def create_stripe_checkout(
    user_id: int,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """
    Create a Stripe Checkout Session for a plan upgrade.
    Uses STRIPE_SECRET_KEY env var.
    Returns dict with key: checkout_url (str).
    Raises ValueError if plan is invalid or Stripe is not configured.
    Raises RuntimeError on Stripe API error.
    """
    try:
        import stripe as _stripe
    except ImportError:
        raise RuntimeError("stripe package not installed — run: pip install stripe")

    if not STRIPE_SECRET_KEY:
        raise ValueError("Stripe not configured — set STRIPE_SECRET_KEY env var")

    plan_info = PLANS.get(plan)
    if not plan_info or plan_info["price_usd"] == 0:
        raise ValueError(f"Invalid or free plan: {plan!r}")

    _stripe.api_key = STRIPE_SECRET_KEY
    amount_cents = int(plan_info["price_usd"] * 100)
    label = plan_info["label"]

    logger.info(
        "[payments] create_stripe_checkout user_id=%s plan=%s amount_usd=%.2f",
        user_id, plan, plan_info["price_usd"],
    )

    try:
        session = _stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount_cents,
                    "product_data": {"name": f"ResumeAI {label} — 1 month"},
                    "recurring": {"interval": "month"},
                },
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user_id), "plan": plan},
        )
        return {"checkout_url": session.url}
    except Exception as exc:
        logger.exception("[payments] create_stripe_checkout error: %s", exc)
        raise RuntimeError(f"Stripe error: {exc}") from exc


async def verify_stripe_webhook(payload: bytes, signature: str) -> dict:
    """
    Verify Stripe webhook signature and parse the event.
    Returns parsed event dict.
    Raises ValueError on invalid signature.
    """
    try:
        import stripe as _stripe
    except ImportError:
        raise RuntimeError("stripe package not installed")

    _stripe.api_key = STRIPE_SECRET_KEY

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = _stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
        else:
            import json as _json
            event = _stripe.Event.construct_from(_json.loads(payload), _stripe.api_key)
        return dict(event)
    except Exception as exc:
        raise ValueError(f"Invalid Stripe webhook signature: {exc}") from exc


# ── Telegram notification ─────────────────────────────────────────────────────

async def send_telegram_message(chat_id: int, text: str) -> None:
    """Send a plain-text message via the existing bot token."""
    if not BOT_TOKEN:
        logger.warning("[payments] BOT_TOKEN not set — cannot send Telegram message")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    body = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=body,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                result = await resp.json()
                if not result.get("ok"):
                    logger.warning(
                        "[payments] send_telegram_message to %s failed: %s",
                        chat_id, result,
                    )
    except aiohttp.ClientError as exc:
        logger.exception(
            "[payments] send_telegram_message network error to %s: %s", chat_id, exc
        )
