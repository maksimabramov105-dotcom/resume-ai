"""
config.py — AutoApply configuration
All secrets via environment variables, safe defaults for development.
"""
import os

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

# ── hh.ru API ───────────────────────────────────────────────────────────
HH_APP_NAME       = os.getenv("HH_APP_NAME", "ResumeAI-AutoApply/1.0 (resumeai.bot)")
HH_CLIENT_ID      = os.getenv("HH_CLIENT_ID", "")
HH_CLIENT_SECRET  = os.getenv("HH_CLIENT_SECRET", "")
HH_REDIRECT_URI   = os.getenv("HH_REDIRECT_URI", "https://resumeai.bot/app/oauth/hh")

# ── SuperJob API ─────────────────────────────────────────────────────────
SUPERJOB_API_KEY  = os.getenv("SUPERJOB_API_KEY", "")

# ── CryptoBot payments ───────────────────────────────────────────────────
CRYPTOBOT_TOKEN                = os.getenv("CRYPTOBOT_TOKEN", "")
CRYPTOBOT_WEBHOOK_SECRET       = os.getenv("CRYPTOBOT_WEBHOOK_SECRET", "")
# AutoApply-specific CryptoBot token (separate app from the main bot)
CRYPTOBOT_AUTOAPPLY_TOKEN      = os.getenv("CRYPTOBOT_AUTOAPPLY_TOKEN", "")

# ── Server ───────────────────────────────────────────────────────────────
AUTOAPPLY_PORT = int(os.getenv("AUTOAPPLY_PORT", "8080"))
AUTOAPPLY_HOST = os.getenv("AUTOAPPLY_HOST", "0.0.0.0")

# ── Plans ────────────────────────────────────────────────────────────────
PLANS = {
    "free":      {"daily_limit": 3,    "price_rub": 0,    "label": "FREE"},
    "start":     {"daily_limit": 50,   "price_rub": 990,  "label": "СТАРТ"},
    "pro":       {"daily_limit": 200,  "price_rub": 2490, "label": "ПРО"},
    "unlimited": {"daily_limit": 9999, "price_rub": 4990, "label": "БЕЗЛИМИТ"},
}

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
