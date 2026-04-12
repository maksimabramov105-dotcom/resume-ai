"""
email_sender.py — Email sending for AutoApply (verification + password reset).

Uses smtplib (no extra deps). Configure via .env:
  SMTP_HOST        — e.g. smtp.gmail.com or smtp.mail.ru
  SMTP_PORT        — 465 (SSL) or 587 (STARTTLS), default 587
  SMTP_USER        — your email login
  SMTP_PASSWORD    — app password (not account password!)
  SMTP_FROM        — sender address, e.g. noreply@resumeai-bot.ru
  SMTP_USE_SSL     — "1" for port 465, leave empty for STARTTLS (port 587)

Deliverability notes:
  - Validates MX records before sending to avoid bounces from fake/disposable addresses
  - For production, switch to Resend (resend.com) or Brevo for better inbox placement
"""

import dns.resolver
import logging
import os
import re
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

_EMAIL_RE = re.compile(r"^[^@\s]+@([^@\s]+\.[^@\s]+)$")


def validate_email_mx(address: str) -> bool:
    """Return True if the email domain has valid MX or A records.
    Rejects fake/disposable domains before wasting an SMTP connection."""
    m = _EMAIL_RE.match(address.strip().lower())
    if not m:
        return False
    domain = m.group(1)
    try:
        dns.resolver.resolve(domain, "MX", lifetime=5)
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        pass
    except Exception:
        pass
    # Fallback: try A record (some domains use A instead of MX)
    try:
        dns.resolver.resolve(domain, "A", lifetime=5)
        return True
    except Exception:
        pass
    logger.warning("[email] domain %s has no MX/A records — rejecting %s", domain, address)
    return False


def _send(to: str, subject: str, html: str, text: str) -> bool:
    """Send email. Returns True on success."""
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("[email] SMTP not configured — skipping send to %s", to)
        return False

    # Validate MX records — abort early for fake/disposable domains
    if not validate_email_mx(to):
        logger.warning("[email] MX validation failed for %s — skipping send", to)
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
    # Day 0
    lambda email: f"""
<h2>Добро пожаловать в РезюмеАИ! 🎉</h2>
<p>Ваш аккаунт создан. Вот как начать за 30 секунд:</p>
<ol>
  <li>Откройте <a href="{WEBAPP_URL}/app">личный кабинет</a></li>
  <li>Или напишите боту: <a href="https://t.me/topbestworkerbot">@topbestworkerbot</a></li>
  <li>Вставьте ссылку на вакансию → AI создаст резюме за 30 сек</li>
</ol>
<p><strong>Бесплатно доступно:</strong> 1 резюме + 1 письмо + 3 AI-сообщения</p>
<p><a href="{WEBAPP_URL}/app" style="background:#F59E0B;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">Создать первое резюме →</a></p>
""",
    # Day 1
    lambda email: f"""
<h2>Ваше резюме проходит ATS-фильтры? 🤔</h2>
<p>Большинство компаний используют ATS-системы, которые автоматически отсеивают резюме. Средний ATS-скор у кандидатов без оптимизации: <strong>42/100</strong>.</p>
<p>Наши пользователи в среднем получают <strong>89/100</strong> после оптимизации.</p>
<p><a href="{WEBAPP_URL}/app">Проверьте свой ATS-скор бесплатно →</a></p>
""",
    # Day 3
    lambda email: f"""
<h2>Резюме готово — нужно сопроводительное письмо? ✉️</h2>
<p>Исследования показывают: кандидаты с персонализированным сопроводительным письмом получают ответ в 2.5x чаще.</p>
<p>Наш AI создаёт письмо под конкретную вакансию за 15 секунд — профессиональное, без шаблонных фраз.</p>
<p><a href="{WEBAPP_URL}/app">Создать сопроводительное письмо →</a></p>
""",
    # Day 5
    lambda email: f"""
<h2>Готовы к собеседованию? 🎯</h2>
<p>5 вопросов которые вам точно зададут:</p>
<ol>
  <li>«Расскажите о себе» — 90% кандидатов отвечают неправильно</li>
  <li>«Почему вы хотите работать у нас?»</li>
  <li>«Где вы видите себя через 5 лет?»</li>
  <li>«Расскажите о своём самом сложном проекте»</li>
  <li>«Почему вы ушли с прошлого места?»</li>
</ol>
<p>AI-подготовка по методу STAR доступна на ПРО-тарифе. <a href="{WEBAPP_URL}/app">Попробовать →</a></p>
""",
    # Day 7
    lambda email: f"""
<h2>Специальное предложение для вас 🎁</h2>
<p>7 дней ПРО-тарифа за символическую стоимость:</p>
<ul>
  <li>50 авто-откликов в день</li>
  <li>Безлимит резюме и писем</li>
  <li>Полный ATS-анализ с рекомендациями</li>
  <li>Email-дайджест лучших вакансий</li>
</ul>
<p>Напишите <strong>/upgrade</strong> боту <a href="https://t.me/topbestworkerbot">@topbestworkerbot</a> для получения предложения.</p>
""",
    # Day 14
    lambda email: f"""
<h2>Последний шанс: скидка 20% 🔥</h2>
<p>Поиск работы — это марафон, не спринт. Дайте AI-инструментам сделать работу за вас.</p>
<p>Промокод на скидку 20% на первый месяц ПРО: <strong>RESUME20</strong></p>
<p>Действует 48 часов. <a href="{WEBAPP_URL}/app">Активировать скидку →</a></p>
""",
]


def send_drip_email(to: str, step: int) -> bool:
    """Send drip email for given step (0-5)."""
    if step >= len(DRIP_SUBJECTS):
        return False
    subject = DRIP_SUBJECTS[step]
    body_fn = DRIP_BODIES[step]
    body_html = body_fn(to)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[РезюмеАИ] {subject}"
    msg["From"] = SMTP_FROM
    msg["To"] = to

    # Plain text fallback
    import re as _re
    plain = _re.sub(r'<[^>]+>', '', body_html).strip()
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(f"<html><body style='font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:24px;color:#334155;'>{body_html}<hr style='margin-top:32px;border-color:#E2E8F0;'><p style='font-size:12px;color:#94A3B8;'>РезюмеАИ · <a href='{WEBAPP_URL}'>resumeai-bot.ru</a> · <a href='{WEBAPP_URL}/app?unsubscribe=1'>Отписаться</a></p></body></html>", "html", "utf-8"))

    if not SMTP_HOST or not SMTP_USER:
        return False
    try:
        context = ssl.create_default_context()
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as s:
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
                s.ehlo()
                s.starttls(context=context)
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Drip email failed step={step} to={to}: {e}")
        return False


def send_password_reset_email(to: str, token: str) -> bool:
    """Send password reset link."""
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
