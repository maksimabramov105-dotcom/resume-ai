"""
email_sender.py — Email sending for AutoApply (verification + password reset).

Uses smtplib (no extra deps). Configure via .env:
  SMTP_HOST        — e.g. smtp.gmail.com or smtp.mail.ru
  SMTP_PORT        — 465 (SSL) or 587 (STARTTLS), default 587
  SMTP_USER        — your email login
  SMTP_PASSWORD    — app password (not account password!)
  SMTP_FROM        — sender address, e.g. noreply@resumeai-bot.ru
  SMTP_USE_SSL     — "1" for port 465, leave empty for STARTTLS (port 587)
"""

import logging
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST     = os.getenv("SMTP_HOST", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_USE_SSL  = os.getenv("SMTP_USE_SSL", "").strip() in ("1", "true", "yes")

WEBAPP_URL = os.getenv("WEBAPP_BASE_URL", "https://resumeai-bot.ru")


def _send(to: str, subject: str, html: str, text: str) -> bool:
    """Send email. Returns True on success."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("[email] SMTP not configured — skipping send to %s", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"АвтоОтклик <{SMTP_FROM}>"
    msg["To"]      = to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html",  "utf-8"))

    try:
        context = ssl.create_default_context()
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as srv:
                srv.login(SMTP_USER, SMTP_PASSWORD)
                srv.sendmail(SMTP_FROM, to, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as srv:
                srv.ehlo()
                srv.starttls(context=context)
                srv.login(SMTP_USER, SMTP_PASSWORD)
                srv.sendmail(SMTP_FROM, to, msg.as_string())
        logger.info("[email] sent '%s' to %s", subject, to)
        return True
    except Exception as exc:
        logger.error("[email] failed to send to %s: %s", to, exc)
        return False


def send_verification_email(to: str, token: str) -> bool:
    """Send email verification link."""
    link = f"{WEBAPP_URL}/app/verify-email?token={token}"
    subject = "Подтвердите email — АвтоОтклик"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#f0f0f0;margin:0;padding:0;">
  <div style="max-width:520px;margin:40px auto;background:#141414;border:1px solid #2a2a2a;border-radius:12px;overflow:hidden;">
    <div style="padding:24px 28px 20px;border-bottom:1px solid #2a2a2a;">
      <span style="font-size:18px;font-weight:700;background:linear-gradient(135deg,#9f5cf7,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">АвтоОтклик</span>
      <span style="font-size:12px;color:#888;margin-left:8px;">by resumeai.bot</span>
    </div>
    <div style="padding:28px;">
      <h2 style="margin:0 0 12px;font-size:20px;font-weight:600;">Подтвердите ваш email</h2>
      <p style="color:#aaa;line-height:1.6;margin:0 0 24px;">
        Для завершения регистрации нажмите кнопку ниже. Ссылка действительна <strong style="color:#f0f0f0;">24 часа</strong>.
      </p>
      <a href="{link}" style="display:inline-block;background:#7c3aed;color:#fff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;">
        Подтвердить email →
      </a>
      <p style="color:#555;font-size:12px;margin:24px 0 0;line-height:1.5;">
        Если вы не регистрировались в АвтоОтклик — просто проигнорируйте это письмо.<br>
        Прямая ссылка: <a href="{link}" style="color:#7c3aed;">{link}</a>
      </p>
    </div>
    <div style="padding:16px 28px;border-top:1px solid #2a2a2a;font-size:11px;color:#444;">
      © АвтоОтклик · <a href="https://resumeai-bot.ru" style="color:#555;">resumeai-bot.ru</a>
    </div>
  </div>
</body>
</html>"""

    text = f"""Подтвердите ваш email — АвтоОтклик

Для завершения регистрации перейдите по ссылке:
{link}

Ссылка действительна 24 часа.

Если вы не регистрировались — просто проигнорируйте это письмо.
"""
    return _send(to, subject, html, text)


def send_welcome_email(to: str) -> bool:
    """Send welcome email after successful verification."""
    subject = "Добро пожаловать в АвтоОтклик!"
    app_link = f"{WEBAPP_URL}/app"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#f0f0f0;margin:0;padding:0;">
  <div style="max-width:520px;margin:40px auto;background:#141414;border:1px solid #2a2a2a;border-radius:12px;overflow:hidden;">
    <div style="padding:24px 28px 20px;border-bottom:1px solid #2a2a2a;">
      <span style="font-size:18px;font-weight:700;background:linear-gradient(135deg,#9f5cf7,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">АвтоОтклик</span>
    </div>
    <div style="padding:28px;">
      <h2 style="margin:0 0 12px;font-size:20px;font-weight:600;">Email подтверждён ✓</h2>
      <p style="color:#aaa;line-height:1.6;margin:0 0 20px;">
        Ваш аккаунт активирован. Вот как начать:
      </p>
      <ol style="color:#aaa;line-height:2;padding-left:20px;margin:0 0 24px;">
        <li>Установите <strong style="color:#f0f0f0;">Chrome Extension</strong> АвтоОтклик</li>
        <li>Войдите в расширение с этим email</li>
        <li>Создайте первую кампанию в <a href="{app_link}" style="color:#9f5cf7;">панели управления</a></li>
        <li>Откройте LinkedIn — бот начнёт откликаться автоматически</li>
      </ol>
      <a href="{app_link}" style="display:inline-block;background:#7c3aed;color:#fff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;">
        Открыть панель управления →
      </a>
    </div>
    <div style="padding:16px 28px;border-top:1px solid #2a2a2a;font-size:11px;color:#444;">
      Бесплатный план: 3 отклика в день. <a href="{app_link}#plans" style="color:#7c3aed;">Upgrade →</a>
    </div>
  </div>
</body>
</html>"""

    text = f"""Email подтверждён — АвтоОтклик

Ваш аккаунт активирован! Как начать:

1. Установите Chrome Extension АвтоОтклик
2. Войдите с этим email и паролем
3. Создайте кампанию: {app_link}
4. Откройте LinkedIn — бот начнёт откликаться

Панель управления: {app_link}
"""
    return _send(to, subject, html, text)


def send_password_reset_email(to: str, token: str) -> bool:
    """Send password reset link."""
    link = f"{WEBAPP_URL}/app/reset-password?token={token}"
    subject = "Сброс пароля — АвтоОтклик"

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#f0f0f0;margin:0;padding:0;">
  <div style="max-width:520px;margin:40px auto;background:#141414;border:1px solid #2a2a2a;border-radius:12px;overflow:hidden;">
    <div style="padding:24px 28px 20px;border-bottom:1px solid #2a2a2a;">
      <span style="font-size:18px;font-weight:700;background:linear-gradient(135deg,#9f5cf7,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">АвтоОтклик</span>
    </div>
    <div style="padding:28px;">
      <h2 style="margin:0 0 12px;font-size:20px;font-weight:600;">Сброс пароля</h2>
      <p style="color:#aaa;line-height:1.6;margin:0 0 24px;">
        Вы запросили сброс пароля. Нажмите кнопку ниже — ссылка действительна <strong style="color:#f0f0f0;">1 час</strong>.
      </p>
      <a href="{link}" style="display:inline-block;background:#7c3aed;color:#fff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;">
        Установить новый пароль →
      </a>
      <p style="color:#555;font-size:12px;margin:24px 0 0;line-height:1.5;">
        Если вы не запрашивали сброс пароля — просто проигнорируйте это письмо. Ваш пароль не изменится.<br>
        Прямая ссылка: <a href="{link}" style="color:#7c3aed;">{link}</a>
      </p>
    </div>
    <div style="padding:16px 28px;border-top:1px solid #2a2a2a;font-size:11px;color:#444;">
      © АвтоОтклик · <a href="https://resumeai-bot.ru" style="color:#555;">resumeai-bot.ru</a>
    </div>
  </div>
</body>
</html>"""

    text = f"""Сброс пароля — АвтоОтклик

Для установки нового пароля перейдите по ссылке:
{link}

Ссылка действительна 1 час.

Если вы не запрашивали сброс — просто проигнорируйте это письмо.
"""
    return _send(to, subject, html, text)
