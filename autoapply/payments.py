"""
payments.py — CryptoBot payment integration for AutoApply
Uses CRYPTOBOT_AUTOAPPLY_TOKEN (separate from main bot's payment token)

API docs: https://help.crypt.bot/crypto-pay-api
"""
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Optional

import aiohttp
import aiosqlite

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

CRYPTOBOT_AUTOAPPLY_TOKEN = os.getenv("CRYPTOBOT_AUTOAPPLY_TOKEN", "")
CRYPTOPAY_API = "https://pay.crypt.bot/api"
USDT_RUB_RATE = float(os.getenv("USDT_RUB_RATE", "90"))

# Telegram API base URL — resolved at import time so BOT_TOKEN env var is read correctly
_TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ── Invoice creation ──────────────────────────────────────────────────────────

async def create_invoice(user_id: int, plan: str, db_path: str = AUTOAPPLY_DB) -> dict:
    """
    Create a CryptoBot invoice for a plan upgrade.
    Converts plan price from RUB to USDT using USDT_RUB_RATE.
    Returns dict with keys: invoice_url (str), invoice_id (int).
    Raises ValueError if CRYPTOBOT_AUTOAPPLY_TOKEN is not configured.
    Raises RuntimeError on CryptoBot API error.
    """
    if not CRYPTOBOT_AUTOAPPLY_TOKEN:
        raise ValueError(
            "CryptoBot token not configured — set CRYPTOBOT_AUTOAPPLY_TOKEN env var"
        )

    plan_info = PLANS.get(plan)
    if not plan_info or plan_info["price_rub"] == 0:
        raise ValueError(f"Invalid or free plan: {plan!r}")

    amount_rub = plan_info["price_rub"]
    amount_usdt = round(amount_rub / USDT_RUB_RATE, 2)

    payload_str = f"{user_id}_{plan}"

    request_body = {
        "asset": "USDT",
        "amount": str(amount_usdt),
        "description": f"АвтоОтклик {plan.upper()} — 1 месяц",
        "payload": payload_str,
        "expires_in": 3600,
        "paid_btn_name": "callback",
        "paid_btn_url": f"{WEBAPP_BASE_URL}/app#pricing",
    }

    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_AUTOAPPLY_TOKEN,
        "Content-Type": "application/json",
    }

    logger.info(
        "[payments] create_invoice user_id=%s plan=%s amount_rub=%s amount_usdt=%s",
        user_id, plan, amount_rub, amount_usdt,
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CRYPTOPAY_API}/createInvoice",
                headers=headers,
                json=request_body,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()

        if not data.get("ok"):
            error = data.get("error", {})
            logger.error("[payments] create_invoice failed: %s", error)
            raise RuntimeError(f"CryptoBot error: {error}")

        result = data["result"]
        invoice_url = result.get("pay_url") or result.get("bot_invoice_url", "")
        invoice_id = result.get("invoice_id")

        logger.info("[payments] invoice created invoice_id=%s", invoice_id)
        return {
            "invoice_url": invoice_url,
            "invoice_id": invoice_id,
        }

    except aiohttp.ClientError as exc:
        logger.exception("[payments] create_invoice network error: %s", exc)
        raise


# ── Webhook verification ──────────────────────────────────────────────────────

async def verify_webhook(payload: bytes, signature: str) -> bool:
    """
    Verify CryptoBot webhook HMAC-SHA256 signature.
    key   = CRYPTOBOT_AUTOAPPLY_TOKEN
    message = raw payload bytes
    Expected signature format: hex digest.
    Returns True if signatures match (or if token is not set, allows through in dev).
    """
    if not CRYPTOBOT_AUTOAPPLY_TOKEN:
        logger.warning(
            "[payments] CRYPTOBOT_AUTOAPPLY_TOKEN not set — skipping webhook verification"
        )
        return True  # Allow in dev; tighten in production

    if not signature:
        return False

    expected = hmac.new(
        CRYPTOBOT_AUTOAPPLY_TOKEN.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature.lower())


# ── Invoice status check ──────────────────────────────────────────────────────

async def get_invoice_status(invoice_id: int) -> str:
    """
    GET /getInvoices?invoice_ids={invoice_id}
    Returns one of: "paid", "pending", "expired", "error"
    """
    if not CRYPTOBOT_AUTOAPPLY_TOKEN:
        logger.warning("[payments] CRYPTOBOT_AUTOAPPLY_TOKEN not set")
        return "error"

    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_AUTOAPPLY_TOKEN}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{CRYPTOPAY_API}/getInvoices",
                headers=headers,
                params={"invoice_ids": str(invoice_id)},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()

        if not data.get("ok"):
            logger.error("[payments] get_invoice_status error: %s", data.get("error"))
            return "error"

        items = data.get("result", {}).get("items", [])
        if not items:
            return "error"

        status = items[0].get("status", "error")
        return status  # "paid", "active" (pending), "expired"

    except aiohttp.ClientError as exc:
        logger.exception("[payments] get_invoice_status network error: %s", exc)
        return "error"


# ── Payment processing ────────────────────────────────────────────────────────

async def process_payment(payload: dict, db_path: str = AUTOAPPLY_DB) -> bool:
    """
    Handle a confirmed CryptoBot webhook event (update_type == "invoice_paid").
    Parses user_id and plan from payload field (format: "{user_id}_{plan}").
    Updates DB plan + daily_limit and sends Telegram notification.
    Returns True on success, False on any failure.
    """
    update_type = payload.get("update_type")
    if update_type != "invoice_paid":
        logger.info("[payments] process_payment: ignoring update_type=%s", update_type)
        return False

    invoice = payload.get("payload", {})
    if not isinstance(invoice, dict):
        invoice = payload

    raw_payload: str = invoice.get("payload") or ""
    logger.info("[payments] processing paid invoice, raw_payload=%r", raw_payload)

    # Parse "{user_id}_{plan}"
    user_id: Optional[int] = None
    plan: Optional[str] = None

    try:
        parts = raw_payload.split("_", 1)
        user_id = int(parts[0])
        plan = parts[1]
    except (ValueError, IndexError):
        logger.error(
            "[payments] Cannot parse user_id/plan from payload: %r", raw_payload
        )
        return False

    plan_info = PLANS.get(plan)
    if not plan_info:
        logger.error("[payments] Unknown plan: %r", plan)
        return False

    daily_limit = plan_info["daily_limit"]

    # Update user plan in DB (autoapply_users has no updated_at column)
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                UPDATE autoapply_users
                SET plan = ?, daily_limit = ?
                WHERE id = ?
                """,
                (plan, daily_limit, user_id),
            )
            rows_affected = db.total_changes
            await db.commit()

        if rows_affected == 0:
            logger.warning(
                "[payments] process_payment: user_id=%s not found in DB", user_id
            )
    except Exception as exc:
        logger.exception("[payments] process_payment DB error: %s", exc)
        return False

    logger.info("[payments] user_id=%s upgraded to plan=%s (limit=%s)", user_id, plan, daily_limit)

    # Fetch telegram_id for notification
    telegram_id: Optional[int] = None
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT telegram_id FROM autoapply_users WHERE id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    telegram_id = row["telegram_id"]
    except Exception as exc:
        logger.exception("[payments] process_payment: failed to fetch telegram_id: %s", exc)

    # Notify user
    if telegram_id:
        user_text = (
            f"Оплата получена! Тариф {plan.upper()} активирован.\n"
            f"Лимит: {daily_limit} заявок/день\n"
            f"Открыть панель: {WEBAPP_BASE_URL}/app"
        )
        await send_telegram_message(telegram_id, user_text)

    # Notify admin
    admin_text = (
        f"Новая оплата AutoApply\n"
        f"User ID: {user_id} | Telegram: {telegram_id}\n"
        f"План: {plan.upper()} | Лимит: {daily_limit}/день"
    )
    await send_telegram_message(ADMIN_CHAT_ID, admin_text)

    return True


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
