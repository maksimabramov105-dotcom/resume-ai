"""
config.py — AutoApply configuration
All secrets via environment variables, safe defaults for development.
"""
import json
import os
from pathlib import Path

# ── Database paths ──────────────────────────────────────────────────────
AUTOAPPLY_DB = os.getenv("AUTOAPPLY_DB", "/opt/resumeaibot/autoapply.db")
BOT_DB       = os.getenv("BOT_DB",       "/opt/resumeaibot/bot.db")
LOGS_DIR     = os.getenv("LOGS_DIR",     "/opt/resumeaibot/logs")

# ── JWT ─────────────────────────────────────────────────────────────────
JWT_SECRET    = os.getenv("JWT_SECRET", "autoapply-change-in-production-2025")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7   # 7 days

# ── Telegram ─────────────────────────────────────────────────────────────
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID  = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "https://resumeai.bot")

# ── OpenAI ───────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── English job board APIs ────────────────────────────────────────────────
ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
ENGLISH_JOB_SOURCES: list = [
    s.strip()
    for s in os.getenv("ENGLISH_JOB_SOURCES", "adzuna,themuse,arbeitnow,remoteok").split(",")
    if s.strip()
]

# ── CryptoBot payments ───────────────────────────────────────────────────
CRYPTOBOT_TOKEN                = os.getenv("CRYPTOBOT_TOKEN", "")
CRYPTOBOT_WEBHOOK_SECRET       = os.getenv("CRYPTOBOT_WEBHOOK_SECRET", "")
# AutoApply-specific CryptoBot token (separate app from the main bot)
CRYPTOBOT_AUTOAPPLY_TOKEN      = os.getenv("CRYPTOBOT_AUTOAPPLY_TOKEN", "")

# ── Stripe payments ──────────────────────────────────────────────────────────
STRIPE_SECRET_KEY       = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET   = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PUBLISHABLE_KEY  = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

# ── Telegram link SSO ────────────────────────────────────────────────────
# Shared secret between bot and autoapply for one-time link tokens.
# Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
LINK_SECRET: str = os.getenv("LINK_SECRET", "")

# ── Country blocklist ────────────────────────────────────────────────────
# Comma-separated ISO-3166-1 alpha-2 codes the worker must never apply to.
# Extend via env: COUNTRY_BLOCKLIST=RU,BY,KP
_raw_blocklist = os.getenv("COUNTRY_BLOCKLIST", "RU,BY")
COUNTRY_BLOCKLIST: frozenset = frozenset(
    c.strip().upper() for c in _raw_blocklist.split(",") if c.strip()
)

# STRICT_DOMICILE=1 (default): vacancies whose company country cannot be
# resolved are blocked.  Set to 0 in dev to allow unknown-country vacancies.
STRICT_DOMICILE: bool = os.getenv("STRICT_DOMICILE", "1").strip() not in ("0", "false", "no", "off")

# ── Feature flags ────────────────────────────────────────────────────────
# Set AUTOAPPLY_ENABLED=0 to pause all automatic job applications without
# stopping the web service (users can still log in and manage campaigns).
AUTOAPPLY_ENABLED: bool = os.getenv("AUTOAPPLY_ENABLED", "1").strip() not in ("0", "false", "no", "off")

# ── Server ───────────────────────────────────────────────────────────────
AUTOAPPLY_PORT = int(os.getenv("AUTOAPPLY_PORT", "8080"))
AUTOAPPLY_HOST = os.getenv("AUTOAPPLY_HOST", "0.0.0.0")

# ── Plans — loaded from pricing.json (single source of truth) ────────────
_PRICING_FILE = Path(__file__).parent.parent / "pricing.json"
try:
    with open(_PRICING_FILE) as _f:
        _raw = json.load(_f)
    PLANS = {
        k: v for k, v in _raw.items()
        if not k.startswith("_")  # skip comment keys
    }
except (FileNotFoundError, json.JSONDecodeError):
    # Hard fallback — should never be needed in production (USD-only since 2026-05 international pivot)
    PLANS = {
        "free":      {"daily_limit": 3,    "price_usd": 0,     "trial_days": 0,  "label": "Free"},
        "trial":     {"daily_limit": 30,   "price_usd": 2.99,  "trial_days": 14, "label": "Trial"},
        "pro":       {"daily_limit": 50,   "price_usd": 19.99, "trial_days": 0,  "label": "Pro"},
        "unlimited": {"daily_limit": 9999, "price_usd": 29.99, "trial_days": 0,  "label": "Unlimited"},
    }

# ── Inbox webhook ────────────────────────────────────────────────────────
# Set INBOX_WEBHOOK_SECRET to a strong random string in production.
# If empty, signature check is skipped with a warning (dev mode only).
INBOX_WEBHOOK_SECRET: str = os.getenv("INBOX_WEBHOOK_SECRET", "")

# ── Delays between applications (seconds) ────────────────────────────────
MIN_APPLY_DELAY = int(os.getenv("MIN_APPLY_DELAY", "30"))
MAX_APPLY_DELAY = int(os.getenv("MAX_APPLY_DELAY", "90"))
WORKER_INTERVAL = int(os.getenv("WORKER_INTERVAL", "300"))  # 5 minutes

# ── SMTP (email verification + password reset) ────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_USE_SSL  = os.getenv("SMTP_USE_SSL", "").strip() in ("1", "true", "yes")
