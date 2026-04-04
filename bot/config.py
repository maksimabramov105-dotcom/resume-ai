import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MODEL_PREMIUM = os.getenv("OPENAI_MODEL_PREMIUM", "gpt-4o")

# Payment (ЮKassa)
YUKASSA_SHOP_ID = os.getenv("YUKASSA_SHOP_ID", "")
YUKASSA_SECRET_KEY = os.getenv("YUKASSA_SECRET_KEY", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

# AI Assistant
ASSISTANT_FREE_MESSAGES = int(os.getenv("ASSISTANT_FREE_MESSAGES", "3"))
ASSISTANT_MAX_CONTEXT_MESSAGES = int(os.getenv("ASSISTANT_MAX_CONTEXT_MESSAGES", "10"))

# Pricing / tariff plans
PRICING = {
    # ===== MAIN PACKAGES =====
    "basic": {
        "name": "📄 Базовый",
        "price_rub": 299,
        "credits_resume": 3,
        "credits_cover_letter": 3,
        "credits_interview": 1,
        "credits_assistant": 10,
        "description": "3 резюме + 3 письма + 1 собес + 10 сообщений AI",
    },
    "pro": {
        "name": "⭐ Про",
        "price_rub": 790,
        "credits_resume": 10,
        "credits_cover_letter": 10,
        "credits_interview": 5,
        "credits_assistant": 50,
        "description": "10 резюме + 10 писем + 5 собесов + 50 сообщений AI",
    },
    "vip": {
        "name": "👑 VIP (30 дней)",
        "price_rub": 1990,
        "credits_resume": 999,
        "credits_cover_letter": 999,
        "credits_interview": 999,
        "credits_assistant": 999,
        "duration_days": 30,
        "description": "Безлимит на 30 дней: всё включено + AI-ассистент",
    },
    # ===== AI ASSISTANT PACKAGES =====
    "assistant_50": {
        "name": "💬 50 сообщений AI",
        "price_rub": 149,
        "credits_assistant": 50,
        "description": "50 сообщений AI-ассистенту (любые вопросы)",
    },
    "assistant_200": {
        "name": "💬 200 сообщений AI",
        "price_rub": 399,
        "credits_assistant": 200,
        "description": "200 сообщений AI-ассистенту (любые вопросы)",
    },
    "assistant_unlimited": {
        "name": "💬 AI Безлимит (30 дней)",
        "price_rub": 690,
        "credits_assistant": 999,
        "duration_days": 30,
        "description": "Безлимитный AI-ассистент на 30 дней",
    },
}
