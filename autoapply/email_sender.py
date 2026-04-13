"""
email_sender.py — Bulletproof email delivery for AutoApply.

Layer 1 (primary):  Resend HTTP API  — most reliable, direct API call
Layer 2 (fallback): SMTP             — works if API is down
Layer 3 (rescue):   Telegram alert   — admin gets link to forward manually

Configure via .env:
  RESEND_API_KEY   — from resend.com dashboard
  RESEND_FROM      — verified sender, e.g. noreply@resumeai-bot.ru
  SMTP_HOST        — e.g. smtp.resend.com
  SMTP_PORT        — 465 (SSL) or 587 (STARTTLS), default 465
  SMTP_USER        — resend
  SMTP_PASSWORD    — same as RESEND_API_KEY
  SMTP_FROM        — same as RESEND_FROM
  SMTP_USE_SSL     — "1" for port 465
  ADMIN_BOT_TOKEN  — Telegram bot token (optional, for rescue layer)
  ADMIN_CHAT_ID    — Telegram admin chat ID (optional)
  WEBAPP_BASE_URL  — e.g. https://resumeai-bot.ru
"""

import dns.resolver
import json
import logging
import os
import re
import smtplib
import ssl
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────────
RESEND_API_KEY = os.getenv("RESEND_API_KEY") or os.getenv("SMTP_PASSWORD", "")
RESEND_FROM    = os.getenv("RESEND_FROM") or os.getenv("SMTP_FROM", "")

SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.resend.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER     = os.getenv("SMTP_USER", "resend")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM", RESEND_FROM)
SMTP_USE_SSL  = os.getenv("SMTP_USE_SSL", "1").strip() in ("1", "true", "yes")

ADMIN_BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID   = os.getenv("ADMIN_CHAT_ID", "")
WEBAPP_URL      = os.getenv("WEBAPP_BASE_URL", "https://resumeai-bot.ru")

_EMAIL_RE = re.compile(r"^[^@\s]+@([^@\s]+\.[^@\s]+)$")


# ── MX validation ──────────────────────────────────────────────────────────────
def validate_email_mx(address: str) -> bool:
    """Return True if the email domain has valid MX or A records."""
    m = _EMAIL_RE.match(address.strip().lower())
    if not m:
        return False
    domain = m.group(1)
    try:
        dns.resolver.resolve(domain, "MX", lifetime=5)
        return True
    except Exception:
        pass
    try:
        dns.resolver.resolve(domain, "A", lifetime=5)
        return True
    except Exception:
        pass
    logger.warning("[email] domain %s has no MX/A records — rejecting %s", domain, address)
    return False


# ── Layer 1: Resend HTTP API ───────────────────────────────────────────────────
def _send_via_resend_api(to: str, subject: str, html: str, text: str) -> bool:
    """Send via Resend HTTP API. No SMTP, no dependency on port 465."""
    if not RESEND_API_KEY or not RESEND_FROM:
        return False
    # Use noreply@resumeai-bot.ru if RESEND_FROM is still the test address
    from_addr = RESEND_FROM
    if "resend.dev" in from_addr:
        from_addr = "noreply@resumeai-bot.ru"

    payload = json.dumps({
        "from": f"АвтоОтклик <{from_addr}>",
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            logger.info("[email/resend-api] sent '%s' to %s — %s", subject, to, body[:80])
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        logger.error("[email/resend-api] HTTP %s for %s: %s", e.code, to, err_body)
    except Exception as exc:
        logger.error("[email/resend-api] failed for %s: %s", to, exc)
    return False


# ── Layer 2: SMTP fallback ─────────────────────────────────────────────────────
def _send_via_smtp(to: str, subject: str, html: str, text: str) -> bool:
    """Send via SMTP. Fallback if HTTP API fails."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        return False

    from_addr = SMTP_FROM
    if "resend.dev" in from_addr:
        from_addr = "noreply@resumeai-bot.ru"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"АвтоОтклик <{from_addr}>"
    msg["To"]      = to
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html",  "utf-8"))

    try:
        context = ssl.create_default_context()
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as srv:
                srv.login(SMTP_USER, SMTP_PASSWORD)
                srv.sendmail(from_addr, to, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=context)
                srv.login(SMTP_USER, SMTP_PASSWORD)
                srv.sendmail(from_addr, to, msg.as_string())
        logger.info("[email/smtp] sent '%s' to %s", subject, to)
        return True
    except Exception as exc:
        logger.error("[email/smtp] failed to send to %s: %s", to, exc)
        return False


# ── Layer 3: Telegram admin rescue ────────────────────────────────────────────
def _alert_admin_email_failed(to: str, subject: str, body_text: str) -> None:
    """Last resort: alert admin via Telegram so they can forward manually."""
    if not ADMIN_BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("[email/rescue] no admin bot config — cannot alert")
        return
    message = (
        f"⚠️ Email delivery failed!\n"
        f"To: {to}\n"
        f"Subject: {subject}\n\n"
        f"Content:\n{body_text[:800]}"
    )
    payload = json.dumps({
        "chat_id": ADMIN_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        logger.info("[email/rescue] admin alerted for %s", to)
    except Exception as exc:
        logger.error("[email/rescue] failed to alert admin: %s", exc)


# ── Main send function ─────────────────────────────────────────────────────────
def _send(to: str, subject: str, html: str, text: str) -> bool:
    """Try all 3 layers. Returns True if any succeeded."""
    # Basic format check
    if not _EMAIL_RE.match(to.strip().lower()):
        logger.warning("[email] invalid address format: %s", to)
        return False

    # MX validation — skip fake/disposable addresses
    if not validate_email_mx(to):
        logger.warning("[email] MX validation failed for %s — skipping", to)
        return False

    # Layer 1: Resend HTTP API
    if _send_via_resend_api(to, subject, html, text):
        return True

    logger.warning("[email] Resend API failed for %s — trying SMTP fallback", to)

    # Layer 2: SMTP
    if _send_via_smtp(to, subject, html, text):
        return True

    logger.error("[email] ALL delivery methods failed for %s — alerting admin", to)

    # Layer 3: Alert admin
    _alert_admin_email_failed(to, subject, text)
    return False


# ── Verification email ─────────────────────────────────────────────────────────
def send_verification_email(to: str, token: str) -> bool:
    link = f"{WEBAPP_URL}/api/verify-email?token={token}"
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


# ── Welcome email ──────────────────────────────────────────────────────────────
def send_welcome_email(to: str) -> bool:
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
      <p style="color:#aaa;line-height:1.6;margin:0 0 20px;">Ваш аккаунт активирован. Вот как начать:</p>
      <ol style="color:#aaa;line-height:2;padding-left:20px;margin:0 0 24px;">
        <li>Загрузите ваше резюме в <a href="{app_link}" style="color:#9f5cf7;">панели управления</a></li>
        <li>Создайте первую кампанию авто-откликов</li>
        <li>Укажите желаемую должность — бот начнёт откликаться автоматически</li>
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
1. Загрузите резюме в панели управления: {app_link}
2. Создайте кампанию авто-откликов
3. Бот начнёт откликаться автоматически

Панель управления: {app_link}
"""
    return _send(to, subject, html, text)


# ── Password reset email ───────────────────────────────────────────────────────
def send_password_reset_email(to: str, token: str) -> bool:
    link = f"{WEBAPP_URL}/app?reset_token={token}"
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
        Если вы не запрашивали сброс — просто проигнорируйте это письмо.<br>
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

Для установки нового пароля:
{link}

Ссылка действительна 1 час.
Если вы не запрашивали сброс — просто проигнорируйте это письмо.
"""
    return _send(to, subject, html, text)


# ── Email Drip Sequence ────────────────────────────────────────────────────────

DRIP_SUBJECTS = [
    "Добро пожаловать! Создайте первое резюме за 30 секунд",
    "Ваше резюме проходит ATS-фильтры? Проверьте сейчас",
    "Резюме готово — нужно сопроводительное письмо?",
    "5 вопросов на собеседовании которые вас точно спросят",
    "Специальное предложение: Попробуйте ПРО-тариф",
    "Последний шанс: 20% скидка на первый месяц",
]

DRIP_BODIES = [
    lambda email: f"""
<h2>Добро пожаловать в РезюмеАИ! 🎉</h2>
<p>Ваш аккаунт создан. Вот как начать за 30 секунд:</p>
<ol>
  <li>Откройте <a href="{WEBAPP_URL}/app">личный кабинет</a></li>
  <li>Или напишите боту: <a href="https://t.me/topbestworkerbot">@topbestworkerbot</a></li>
  <li>Вставьте ссылку на вакансию → AI создаст резюме за 30 сек</li>
</ol>
<p><strong>Бесплатно доступно:</strong> 1 резюме + 1 письмо + 3 AI-сообщения</p>
<p><a href="{WEBAPP_URL}/app" style="background:#7c3aed;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">Создать первое резюме →</a></p>
""",
    lambda email: f"""
<h2>Ваше резюме проходит ATS-фильтры? 🤔</h2>
<p>Большинство компаний используют ATS-системы. Средний ATS-скор без оптимизации: <strong>42/100</strong>.</p>
<p>Наши пользователи в среднем получают <strong>89/100</strong> после оптимизации.</p>
<p><a href="{WEBAPP_URL}/app">Проверьте свой ATS-скор бесплатно →</a></p>
""",
    lambda email: f"""
<h2>Резюме готово — нужно сопроводительное письмо? ✉️</h2>
<p>Кандидаты с персонализированным письмом получают ответ в 2.5x чаще.</p>
<p><a href="{WEBAPP_URL}/app">Создать сопроводительное письмо →</a></p>
""",
    lambda email: f"""
<h2>Готовы к собеседованию? 🎯</h2>
<p>5 вопросов которые вам точно зададут:</p>
<ol>
  <li>«Расскажите о себе»</li>
  <li>«Почему вы хотите работать у нас?»</li>
  <li>«Где вы видите себя через 5 лет?»</li>
  <li>«Расскажите о вашем сложном проекте»</li>
  <li>«Почему вы ушли с прошлого места?»</li>
</ol>
<p><a href="{WEBAPP_URL}/app">AI-подготовка по методу STAR →</a></p>
""",
    lambda email: f"""
<h2>Специальное предложение 🎁</h2>
<ul>
  <li>50 авто-откликов в день</li>
  <li>Безлимит резюме и писем</li>
  <li>Полный ATS-анализ</li>
</ul>
<p>Напишите <strong>/upgrade</strong> боту <a href="https://t.me/topbestworkerbot">@topbestworkerbot</a></p>
""",
    lambda email: f"""
<h2>Последний шанс: скидка 20% 🔥</h2>
<p>Промокод: <strong>RESUME20</strong></p>
<p>Действует 48 часов. <a href="{WEBAPP_URL}/app">Активировать →</a></p>
""",
]


def send_drip_email(to: str, step: int) -> bool:
    if step >= len(DRIP_SUBJECTS):
        return False
    subject = f"[РезюмеАИ] {DRIP_SUBJECTS[step]}"
    body_html = DRIP_BODIES[step](to)
    import re as _re
    plain = _re.sub(r'<[^>]+>', '', body_html).strip()
    full_html = (
        f"<html><body style='font-family:Inter,sans-serif;max-width:600px;margin:0 auto;"
        f"padding:24px;color:#334155;'>{body_html}"
        f"<hr style='margin-top:32px;border-color:#E2E8F0;'>"
        f"<p style='font-size:12px;color:#94A3B8;'>РезюмеАИ · "
        f"<a href='{WEBAPP_URL}'>resumeai-bot.ru</a> · "
        f"<a href='{WEBAPP_URL}/app?unsubscribe=1'>Отписаться</a></p></body></html>"
    )
    return _send(to, subject, full_html, plain)
