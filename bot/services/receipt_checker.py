"""
AI-powered receipt verification.

Uses GPT-4o vision (via OpenRouter) to analyse payment screenshots.

Verdicts:
  "approve" — confident it's a real, correct payment → auto-approve
  "manual"  — uncertain or suspicious → forward to admin with AI notes
"""
from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp

from config import OPENROUTER_API_KEY, OPENAI_API_KEY, BOT_TOKEN

logger = logging.getLogger(__name__)

VISION_MODEL = "openai/gpt-4o"   # cheapest model with reliable vision

# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ReceiptResult:
    verdict: str        # "approve" | "manual"
    confidence: float   # 0.0 – 1.0
    reason: str         # one-line verdict reason (for admin caption)
    analysis: str       # full AI analysis text


async def _download_telegram_photo(file_id: str) -> bytes:
    """Download photo bytes from Telegram servers."""
    tg_base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    async with aiohttp.ClientSession() as session:
        # Get file path
        async with session.get(f"{tg_base}/getFile?file_id={file_id}") as resp:
            data = await resp.json()
            file_path = data["result"]["file_path"]

        # Download file
        async with session.get(f"{tg_base}/file/{file_path}") as resp:
            return await resp.read()


def _to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode("utf-8")


def _build_prompt(
    expected_amount_rub: int,
    payment_method: str,
    card_number: Optional[str],
    revolut_tag: Optional[str],
) -> str:
    if payment_method == "rucard":
        payment_info = (
            f"Payment method: Russian bank card transfer.\n"
            f"Expected amount: {expected_amount_rub} RUB.\n"
            f"Expected recipient card number: {card_number}."
        )
    else:
        payment_info = (
            f"Payment method: Revolut transfer.\n"
            f"Expected amount: {expected_amount_rub} RUB (or equivalent in any currency).\n"
            f"Expected Revolut tag / card: {revolut_tag}."
        )

    return f"""You are a payment receipt verification assistant for a Telegram bot service.

A user has submitted a payment screenshot. Your job is to determine whether it is a genuine, successful payment.

{payment_info}

Analyse the screenshot and answer ONLY with a JSON object (no markdown, no extra text):
{{
  "verdict": "approve" or "manual",
  "confidence": <float 0.0-1.0>,
  "reason": "<one short sentence in Russian explaining the verdict>",
  "analysis": "<detailed analysis in Russian: what you see, amount visible, recipient visible, any concerns>"
}}

Rules for "approve":
- The screenshot clearly shows a COMPLETED / SUCCESSFUL transfer (not pending, not initiated)
- The amount matches {expected_amount_rub} RUB (±5% tolerance for currency conversion)
- The screenshot is not obviously edited or fabricated
- The date/time is recent (within last 24 hours if visible)

Rules for "manual" (send to human admin):
- Amount doesn't match
- Transfer is in "pending" or "processing" state only
- Screenshot is blurry or cropped so key info is not visible
- Screenshot looks edited / suspicious (mismatched fonts, copy-paste artefacts)
- It's not a payment receipt at all
- You are not confident enough (confidence < 0.75)

When in doubt, always choose "manual". It is better to be safe than to approve a fake payment.
"""


async def check_receipt(
    file_id: str,
    expected_amount_rub: int,
    payment_method: str,            # "rucard" | "revolut"
    card_number: Optional[str] = None,
    revolut_tag: Optional[str] = None,
) -> ReceiptResult:
    """
    Main entry point.  Downloads the photo, sends to GPT-4o vision,
    returns a ReceiptResult with verdict + analysis.
    """
    try:
        image_bytes = await _download_telegram_photo(file_id)
        b64 = _to_base64(image_bytes)
        prompt = _build_prompt(expected_amount_rub, payment_method, card_number, revolut_tag)

        api_key = OPENROUTER_API_KEY or OPENAI_API_KEY
        base_url = (
            "https://openrouter.ai/api/v1"
            if OPENROUTER_API_KEY
            else "https://api.openai.com/v1"
        )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if OPENROUTER_API_KEY:
            headers["HTTP-Referer"] = "https://t.me/topbestworkerbot"
            headers["X-Title"] = "РезюмеАИ"

        payload = {
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": 500,
            "temperature": 0.1,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=40),
            ) as resp:
                result = await resp.json()

        raw = result["choices"][0]["message"]["content"].strip()

        # Strip markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        parsed = json.loads(raw)
        verdict = parsed.get("verdict", "manual")
        confidence = float(parsed.get("confidence", 0.5))
        reason = parsed.get("reason", "")
        analysis = parsed.get("analysis", "")

        # Extra safety: downgrade to manual if confidence is borderline
        if verdict == "approve" and confidence < 0.80:
            verdict = "manual"
            reason = f"[Низкая уверенность {confidence:.0%}] " + reason

        logger.info(
            "Receipt check: verdict=%s confidence=%.2f reason=%s",
            verdict, confidence, reason
        )
        return ReceiptResult(
            verdict=verdict,
            confidence=confidence,
            reason=reason,
            analysis=analysis,
        )

    except Exception as e:
        logger.exception("Receipt AI check failed: %s", e)
        # On any error — send to admin for manual review
        return ReceiptResult(
            verdict="manual",
            confidence=0.0,
            reason=f"Ошибка AI-проверки: {e}",
            analysis="AI-проверка не удалась. Требуется ручная проверка.",
        )
