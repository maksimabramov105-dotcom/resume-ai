"""
inbox.py — Email threading and rejection classification for the Reply Inbox.

Responsibilities:
  1. parse_reply_to_thread_id(address) -> Optional[int]   extract thread_id from reply-to header
  2. is_rejection(text) -> bool                            tiny keyword classifier
  3. process_inbound_webhook(payload, db_path) -> dict     main webhook handler
  4. send_reply(thread_id, user_id, body_text, db_path)    send email reply + store message
"""
import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# ── Reply-To address pattern ──────────────────────────────────────────────────
# Format: reply+t{thread_id}@apply.resumeai-bot.ru
_THREAD_ID_RE = re.compile(r'\+t(\d+)@', re.IGNORECASE)

# ── Rejection keyword classifier ──────────────────────────────────────────────
_REJECTION_PHRASES = [
    "we regret to inform",
    "regret to let you know",
    "moved forward with other candidates",
    "decided to move forward with other",
    "not moving forward with your application",
    "not selected for",
    "we will not be moving forward",
    "position has been filled",
    "unfortunately",
    "we have decided not to proceed",
    "does not meet our requirements",
    "not a match",
]


def parse_reply_to_thread_id(address: str) -> Optional[int]:
    """Extract thread_id from a reply-to address like reply+t42@apply.resumeai-bot.ru."""
    if not address:
        return None
    m = _THREAD_ID_RE.search(address)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


def is_rejection(text: str) -> bool:
    """Return True if the message text contains a rejection signal."""
    if not text:
        return False
    lower = text.lower()
    for phrase in _REJECTION_PHRASES:
        if phrase in lower:
            logger.info("[inbox] rejection keyword matched: %r", phrase)
            return True
    return False


async def process_inbound_webhook(payload: dict, db_path: str) -> dict:
    """
    Handle Mailgun-style inbound email webhook payload.
    Also handles SES/SNS Notification format.
    Returns dict with thread_id, message_id, status, is_rejection.
    """
    from autoapply.autoapply_db import (
        add_message,
        get_thread_by_id,
        update_thread_status,
    )

    # Support SES/SNS format
    if payload.get("Type") == "Notification":
        try:
            payload = json.loads(payload["Message"])
        except (KeyError, json.JSONDecodeError) as exc:
            logger.warning("[inbox] SES/SNS payload parse error: %s", exc)

    sender = payload.get("sender") or payload.get("from", "")
    recipient = payload.get("recipient") or payload.get("to", "")
    subject = payload.get("subject", "(no subject)")
    body_text = payload.get("body-plain") or payload.get("text", "")
    body_html = payload.get("body-html") or payload.get("html", "")
    message_id = payload.get("Message-Id") or payload.get("message_id", "")
    in_reply_to = payload.get("In-Reply-To") or payload.get("in_reply_to", "")

    # Try to extract thread_id from recipient address
    thread_id = parse_reply_to_thread_id(recipient)
    if not thread_id:
        logger.warning("[inbox] could not resolve thread_id from recipient=%r", recipient)
        return {"thread_id": None, "message_id": message_id, "status": "no_thread", "is_rejection": False}

    # Validate thread exists — we use user_id=0 sentinel to bypass ownership check
    # (we don't have user_id in the webhook context, so we look up directly)
    import aiosqlite
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, user_id, status FROM app_threads WHERE id = ?", (thread_id,)
        ) as cur:
            thread_row = await cur.fetchone()

    if not thread_row:
        logger.warning("[inbox] thread_id=%d not found in DB", thread_id)
        return {"thread_id": thread_id, "message_id": message_id, "status": "thread_not_found", "is_rejection": False}

    user_id = thread_row["user_id"]

    # Store the inbound message
    msg_id = await add_message(
        thread_id=thread_id,
        direction="in",
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        message_id=message_id,
        in_reply_to=in_reply_to,
        db_path=db_path,
    )

    # Classify and update thread status
    rejection = is_rejection(body_text)
    new_status = "rejected" if rejection else "recruiter_replied"
    await update_thread_status(
        thread_id=thread_id,
        status=new_status,
        company_email=sender or None,
        db_path=db_path,
    )

    logger.info(
        "[inbox] inbound message stored: thread_id=%d msg_db_id=%d status=%s is_rejection=%s",
        thread_id, msg_id, new_status, rejection,
    )
    return {
        "thread_id": thread_id,
        "user_id": user_id,
        "message_id": message_id,
        "status": new_status,
        "is_rejection": rejection,
    }


async def send_reply(
    thread_id: int, user_id: int, body_text: str, db_path: str
) -> bool:
    """
    Send an email reply in a thread and store the outbound message row.
    Returns True on success.
    """
    from autoapply.autoapply_db import add_message, get_thread_by_id, get_messages_for_thread
    import aiosqlite

    # Verify ownership
    thread = await get_thread_by_id(thread_id, user_id, db_path=db_path)
    if not thread:
        logger.warning("[inbox] send_reply: thread_id=%d not found for user_id=%d", thread_id, user_id)
        return False

    to_addr = thread.get("company_email", "")
    if not to_addr:
        logger.warning("[inbox] send_reply: no company_email on thread_id=%d", thread_id)
        return False

    # Get last inbound message for threading headers
    messages = await get_messages_for_thread(thread_id, user_id, db_path=db_path)
    last_in = next((m for m in reversed(messages) if m["direction"] == "in"), None)
    original_message_id = (last_in or {}).get("message_id", "")
    original_subject = (last_in or {}).get("subject", "")
    if not original_subject:
        original_subject = thread.get("company_name", "your application")

    subject = f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
    new_message_id = f"<{uuid4().hex}@apply.resumeai-bot.ru>"

    # Build HTML body
    body_html = f"<p>{body_text.replace(chr(10), '<br>')}</p>"

    resend_api_key = os.getenv("RESEND_API_KEY", "")
    resend_from = os.getenv("RESEND_FROM", "") or os.getenv("SMTP_FROM", "")

    sent = False
    if resend_api_key and resend_from:
        # Use Resend API with threading headers
        from_addr = resend_from
        if "resend.dev" in from_addr:
            from_addr = "noreply@resumeai-bot.ru"
        payload = json.dumps({
            "from": f"ResumeAI <{from_addr}>",
            "to": [to_addr],
            "subject": subject,
            "html": body_html,
            "text": body_text,
            "headers": {
                "Message-Id": new_message_id,
                **({"In-Reply-To": original_message_id, "References": original_message_id} if original_message_id else {}),
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
                sent = True
                logger.info("[inbox] sent reply via Resend to %s (thread_id=%d)", to_addr, thread_id)
        except urllib.error.HTTPError as exc:
            err = exc.read().decode()
            logger.error("[inbox] Resend API error %s: %s", exc.code, err)
        except Exception as exc:
            logger.error("[inbox] Resend send error: %s", exc)
    else:
        # SMTP fallback
        import smtplib
        import ssl
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        smtp_host = os.getenv("SMTP_HOST", "")
        smtp_port = int(os.getenv("SMTP_PORT", "465"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        smtp_from = os.getenv("SMTP_FROM", smtp_user)
        smtp_ssl = os.getenv("SMTP_USE_SSL", "1").strip() in ("1", "true", "yes")

        if smtp_host and smtp_user and smtp_password:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"ResumeAI <{smtp_from}>"
            msg["To"] = to_addr
            msg["Message-Id"] = new_message_id
            if original_message_id:
                msg["In-Reply-To"] = original_message_id
                msg["References"] = original_message_id
            msg.attach(MIMEText(body_text, "plain", "utf-8"))
            msg.attach(MIMEText(body_html, "html", "utf-8"))
            try:
                context = ssl.create_default_context()
                if smtp_ssl:
                    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=10) as srv:
                        srv.login(smtp_user, smtp_password)
                        srv.sendmail(smtp_from, to_addr, msg.as_string())
                else:
                    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as srv:
                        srv.ehlo()
                        srv.starttls(context=context)
                        srv.login(smtp_user, smtp_password)
                        srv.sendmail(smtp_from, to_addr, msg.as_string())
                sent = True
                logger.info("[inbox] sent reply via SMTP to %s (thread_id=%d)", to_addr, thread_id)
            except Exception as exc:
                logger.error("[inbox] SMTP send error: %s", exc)
        else:
            logger.warning("[inbox] no email credentials configured — cannot send reply")

    # Store outbound message regardless of delivery (as pending/attempted)
    await add_message(
        thread_id=thread_id,
        direction="out",
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        message_id=new_message_id,
        in_reply_to=original_message_id,
        db_path=db_path,
    )

    return sent
