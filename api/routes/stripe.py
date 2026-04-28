"""
Stripe Checkout and Webhook routes.

POST /api/stripe/create-checkout  — create a Checkout Session for a tier
POST /api/stripe/webhook          — receive Stripe events
"""
import logging
import os
import sys

import aiosqlite
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bot"))

from autoapply.config import (
    AUTOAPPLY_DB,
    BOT_TOKEN,
    PLANS,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)
from autoapply.payments import send_telegram_message

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Price ID mapping (env vars set after running stripe_setup.py) ─────────────
_PRICE_IDS: dict[str, str] = {
    "trial":     os.getenv("STRIPE_PRICE_TRIAL", ""),
    "pro":       os.getenv("STRIPE_PRICE_PRO_MONTHLY", ""),
    "unlimited": os.getenv("STRIPE_PRICE_PREMIUM_MONTHLY", ""),
}

_TIER_MODES: dict[str, str] = {
    "trial":     "payment",       # one-time
    "pro":       "subscription",
    "unlimited": "subscription",
}

BASE_URL = os.getenv("WEBAPP_URL", "https://resumeai-bot.ru")


# ── Schemas ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    user_id: int   # telegram_id
    tier: str      # trial | pro | unlimited


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _save_customer_mapping(telegram_id: int, stripe_customer_id: str) -> None:
    """Persist telegram_id → stripe_customer_id so subscription.deleted can find the user."""
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            # Add column if missing (idempotent)
            try:
                await db.execute(
                    "ALTER TABLE autoapply_users ADD COLUMN stripe_customer_id TEXT"
                )
                await db.commit()
            except Exception:
                pass  # column already exists
            await db.execute(
                "UPDATE autoapply_users SET stripe_customer_id=? WHERE telegram_id=?",
                (stripe_customer_id, telegram_id),
            )
            await db.commit()
    except Exception as exc:
        logger.warning("[stripe] _save_customer_mapping error: %s", exc)


async def _telegram_id_from_customer(stripe_customer_id: str) -> Optional[int]:
    """Look up telegram_id by stripe_customer_id."""
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            async with db.execute(
                "SELECT telegram_id FROM autoapply_users WHERE stripe_customer_id=?",
                (stripe_customer_id,),
            ) as cur:
                row = await cur.fetchone()
                return int(row[0]) if row else None
    except Exception as exc:
        logger.warning("[stripe] _telegram_id_from_customer error: %s", exc)
        return None


async def _activate_subscription(telegram_id: int, tier: str) -> None:
    from datetime import datetime, timedelta
    plan_info = PLANS.get(tier, PLANS.get("pro"))
    daily_limit = plan_info["daily_limit"]
    expires_at = datetime.utcnow() + timedelta(days=30)

    # Update main bot.db subscription
    try:
        from database.db import get_or_create_user, save_user
        user = await get_or_create_user(telegram_id)
        user.subscription_type = tier
        user.subscription_expires = expires_at
        await save_user(user)
    except Exception as exc:
        logger.warning("[stripe] _activate bot.db error: %s", exc)

    # Update autoapply_users plan + limit
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            await db.execute(
                "UPDATE autoapply_users SET plan=?, daily_limit=? WHERE telegram_id=?",
                (tier, daily_limit, telegram_id),
            )
            await db.commit()
    except Exception as exc:
        logger.warning("[stripe] _activate autoapply.db error: %s", exc)


async def _deactivate_subscription(telegram_id: int) -> None:
    try:
        from database.db import get_or_create_user, save_user
        user = await get_or_create_user(telegram_id)
        user.subscription_type = "free"
        user.subscription_expires = None
        await save_user(user)
    except Exception as exc:
        logger.warning("[stripe] _deactivate bot.db error: %s", exc)

    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            await db.execute(
                "UPDATE autoapply_users SET plan='free', daily_limit=3 WHERE telegram_id=?",
                (telegram_id,),
            )
            await db.commit()
    except Exception as exc:
        logger.warning("[stripe] _deactivate autoapply.db error: %s", exc)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/create-checkout")
async def create_checkout(req: CheckoutRequest):
    if req.tier not in _PRICE_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {req.tier}")

    price_id = _PRICE_IDS[req.tier]
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=f"Price not configured for tier '{req.tier}'. Run stripe_setup.py first.",
        )

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")

    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_SECRET_KEY

        session = _stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode=_TIER_MODES[req.tier],
            success_url=f"{BASE_URL}/app/pricing?success=1&tier={req.tier}",
            cancel_url=f"{BASE_URL}/app/pricing?cancelled=1",
            metadata={"user_id": str(req.user_id), "tier": req.tier},
        )
        return {"checkout_url": session.url}

    except Exception as exc:
        logger.exception("[stripe] create_checkout error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
):
    payload = await request.body()

    # Verify signature
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_SECRET_KEY
        if STRIPE_WEBHOOK_SECRET:
            event = _stripe.Webhook.construct_event(
                payload, stripe_signature or "", STRIPE_WEBHOOK_SECRET
            )
        else:
            import json as _json
            event = _stripe.Event.construct_from(_json.loads(payload), _stripe.api_key)
    except Exception as exc:
        logger.warning("[stripe] webhook signature verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    logger.info("[stripe] event type=%s id=%s", event_type, event.get("id"))

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata") or {}
        telegram_id = int(metadata.get("user_id", 0))
        tier = metadata.get("tier", "pro")
        customer_id = session.get("customer")

        if not telegram_id:
            logger.warning("[stripe] checkout.session.completed: missing user_id in metadata")
            return {"received": True}

        # Persist customer_id → telegram_id for future subscription events
        if customer_id:
            await _save_customer_mapping(telegram_id, customer_id)

        await _activate_subscription(telegram_id, tier)

        tier_label = tier.title()
        await send_telegram_message(
            telegram_id,
            f"✅ Payment confirmed! Your {tier_label} subscription is now active.\n\n"
            f"Open your dashboard: {BASE_URL}/app",
        )
        logger.info("[stripe] activated tier=%s telegram_id=%s", tier, telegram_id)

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        telegram_id = await _telegram_id_from_customer(customer_id)
        if not telegram_id:
            logger.warning(
                "[stripe] subscription.deleted: no telegram_id for customer=%s", customer_id
            )
            return {"received": True}

        await _deactivate_subscription(telegram_id)
        await send_telegram_message(
            telegram_id,
            "Your ResumeAI subscription has been cancelled. "
            "You've been moved to the free plan.\n\n"
            f"Re-subscribe anytime at {BASE_URL}/app/pricing",
        )
        logger.info("[stripe] deactivated telegram_id=%s", telegram_id)

    return {"received": True}
