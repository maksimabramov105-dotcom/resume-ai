"""
payments.py — Payment processing for AutoApply.
Uses CryptoBot (@CryptoBot) same as the existing bot.
"""
import hashlib
import hmac
import json
import logging
from typing import Optional

import aiohttp

from autoapply.config import (
    ADMIN_CHAT_ID,
    AUTOAPPLY_DB,
    BOT_TOKEN,
    CRYPTOBOT_TOKEN,
    CRYPTOBOT_WEBHOOK_SECRET,
    PLANS,
    WEBAPP_BASE_URL,
)
from autoapply.autoapply_db import get_user_by_id, update_user_plan

logger = logging.getLogger(__name__)

CRYPTOPAY_API = "https://pay.crypt.bot/api"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Map RUB amounts to plan names
_AMOUNT_TO_PLAN: dict = {
    str(info["price_rub"]): name
    for name, info in PLANS.items()
    if info["price_rub"] > 0
}


# ── Invoice creation ──────────────────────────────────────────────────────────

async def create_invoice(user_id: int, plan: str, db_path: str = AUTOAPPLY_DB) -> dict:
    """
    Create a CryptoBot invoice for a plan upgrade.
    Returns the invoice dict from CryptoBot on success.
    """
    plan_info = PLANS.get(plan)
    if not plan_info or plan_info["price_rub"] == 0:
        raise ValueError(f"Invalid or free plan: {plan}")

    amount_rub = plan_info["price_rub"]
    label = plan_info["label"]

    # CryptoBot works in crypto assets; we use USDT as a stable reference.
    # The description carries the plan key so process_payment can identify it.
    payload_data = json.dumps({"user_id": user_id, "plan": plan})

    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {
        "asset": "USDT",
        "amount": str(amount_rub),          # amount in chosen asset units
        "description": f"AutoApply план {label} | user_id={user_id}",
        "payload": payload_data,
        "allow_comments": False,
        "allow_anonymous": False,
        "expires_in": 3600,                 # 1 hour
    }

    logger.info("[payments] create_invoice user_id=%s plan=%s amount=%s", user_id, plan, amount_rub)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CRYPTOPAY_API}/createInvoice",
                headers=headers,
                json=params,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()

        if not data.get("ok"):
            error = data.get("error", {})
            logger.error("[payments] create_invoice failed: %s", error)
            raise RuntimeError(f"CryptoBot error: {error}")

        invoice = data["result"]
        logger.info("[payments] invoice created: %s", invoice.get("invoice_id"))
        return invoice

    except aiohttp.ClientError as exc:
        logger.exception("[payments] create_invoice network error: %s", exc)
        raise


# ── Webhook verification ──────────────────────────────────────────────────────

async def verify_webhook(payload: bytes, signature: str) -> bool:
    """
    Verify CryptoBot webhook HMAC-SHA256 signature.
    Signature = HMAC-SHA256(webhook_secret, payload_bytes).hexdigest()
    """
    if not CRYPTOBOT_WEBHOOK_SECRET:
        logger.warning("[payments] CRYPTOBOT_WEBHOOK_SECRET not set — skipping verification")
        return True  # Allow in dev; tighten in production

    if not signature:
        return False

    expected = hmac.new(
        CRYPTOBOT_WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature.lower())


# ── Payment processing ────────────────────────────────────────────────────────

async def process_payment(payload: dict, db_path: str = AUTOAPPLY_DB) -> bool:
    """
    Handle a confirmed CryptoBot webhook event.
    Extracts user_id and plan from the invoice payload field,
    upgrades the plan, and sends a Telegram notification.
    """
    update_type = payload.get("update_type")
    if update_type != "invoice_paid":
        logger.info("[payments] ignoring update_type=%s", update_type)
        return False

    invoice = payload.get("payload", {})
    if not isinstance(invoice, dict):
        # Some versions of the webhook wrap it differently
        invoice = payload

    raw_payload = invoice.get("payload") or ""
    logger.info("[payments] processing paid invoice, raw_payload=%r", raw_payload)

    # Try to decode JSON payload set during invoice creation
    user_id: Optional[int] = None
    plan: Optional[str] = None

    try:
        meta = json.loads(raw_payload)
        user_id = int(meta["user_id"])
        plan = meta["plan"]
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        # Fallback: try to derive plan from amount
        amount_str = str(invoice.get("amount", "")).split(".")[0]
        plan = _AMOUNT_TO_PLAN.get(amount_str)
        # user_id must be in description or comment
        description: str = invoice.get("description", "")
        for part in description.split("|"):
            part = part.strip()
            if part.startswith("user_id="):
                try:
                    user_id = int(part.split("=", 1)[1])
                except ValueError:
                    pass

    if not user_id or not plan:
        logger.error(
            "[payments] cannot determine user_id=%s or plan=%s from invoice", user_id, plan
        )
        return False

    user = await get_user_by_id(user_id, db_path)
    if not user:
        logger.error("[payments] user_id=%s not found in autoapply DB", user_id)
        return False

    # Upgrade plan
    await update_user_plan(user_id, plan, db_path)
    logger.info("[payments] user_id=%s upgraded to plan=%s", user_id, plan)

    # Notify user via Telegram (if telegram_id linked)
    telegram_id = user.get("telegram_id")
    plan_label = PLANS.get(plan, {}).get("label", plan)
    daily_limit = PLANS.get(plan, {}).get("daily_limit", 0)

    if telegram_id:
        text = (
            f"Оплата получена!\n\n"
            f"Ваш план: {plan_label}\n"
            f"Лимит откликов в день: {daily_limit}\n\n"
            f"Откройте веб-приложение: {WEBAPP_BASE_URL}/app"
        )
        await send_telegram_message(telegram_id, text)

    # Notify admin
    admin_text = (
        f"Новая оплата AutoApply\n"
        f"User ID: {user_id} | Telegram: {telegram_id}\n"
        f"Plan: {plan_label}"
    )
    await send_telegram_message(ADMIN_CHAT_ID, admin_text)

    return True


# ── Telegram notification ─────────────────────────────────────────────────────

async def send_telegram_message(chat_id: int, text: str) -> None:
    """Send a plain-text message via the existing bot token."""
    if not BOT_TOKEN:
        logger.warning("[payments] BOT_TOKEN not set — cannot send Telegram message")
        return

    url = f"{TELEGRAM_API}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                result = await resp.json()
                if not result.get("ok"):
                    logger.warning(
                        "[payments] send_telegram_message to %s failed: %s", chat_id, result
                    )
    except aiohttp.ClientError as exc:
        logger.exception("[payments] send_telegram_message network error: %s", exc)
