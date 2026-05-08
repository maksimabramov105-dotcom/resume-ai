import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_URL = os.getenv("WEBAPP_URL", "")  # HTTPS URL of the Mini App

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MODEL_PREMIUM = os.getenv("OPENAI_MODEL_PREMIUM", "gpt-4o")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

# AI Assistant
ASSISTANT_FREE_MESSAGES = int(os.getenv("ASSISTANT_FREE_MESSAGES", "3"))
ASSISTANT_MAX_CONTEXT_MESSAGES = int(os.getenv("ASSISTANT_MAX_CONTEXT_MESSAGES", "10"))

# ===== PAYMENT METHODS (international only — 2026-05 pivot) =====

# Revolut — manual transfer, admin approval
REVOLUT_TAG = os.getenv("REVOLUT_TAG", "@yourtag")   # Revolut @tag
REVOLUT_LINK = os.getenv("REVOLUT_LINK", "")          # https://revolut.me/yourtag

# Stripe handled via the web app (WEBAPP_URL/app#pricing)

# Pricing / tariff plans (USD, international)
PRICING = {
    # ===== MAIN PACKAGES =====
    "basic": {
        "name": "📄 Basic",
        "price_usd": 4.99,
        "credits_resume": 3,
        "credits_cover_letter": 3,
        "credits_interview": 1,
        "credits_assistant": 10,
        "description": "3 resumes + 3 cover letters + 1 mock interview + 10 AI messages",
    },
    "pro": {
        "name": "⭐ Pro",
        "price_usd": 9.99,
        "credits_resume": 10,
        "credits_cover_letter": 10,
        "credits_interview": 5,
        "credits_assistant": 50,
        "description": "10 resumes + 10 cover letters + 5 mock interviews + 50 AI messages",
    },
    "vip": {
        "name": "👑 VIP (30 days)",
        "price_usd": 24.99,
        "credits_resume": 999,
        "credits_cover_letter": 999,
        "credits_interview": 999,
        "credits_assistant": 999,
        "duration_days": 30,
        "description": "Unlimited 30-day access: all features + AI assistant",
    },
    # ===== AI ASSISTANT PACKAGES =====
    "assistant_50": {
        "name": "💬 50 AI messages",
        "price_usd": 1.99,
        "credits_assistant": 50,
        "description": "50 AI assistant messages",
    },
    "assistant_200": {
        "name": "💬 200 AI messages",
        "price_usd": 4.99,
        "credits_assistant": 200,
        "description": "200 AI assistant messages",
    },
    "assistant_unlimited": {
        "name": "💬 AI Unlimited (30 days)",
        "price_usd": 8.99,
        "credits_assistant": 999,
        "duration_days": 30,
        "description": "Unlimited AI assistant for 30 days",
    },
}
