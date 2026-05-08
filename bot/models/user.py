from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    full_name = Column(String, nullable=True)

    # Credits for main features
    credits_resume = Column(Integer, default=1)
    credits_cover_letter = Column(Integer, default=1)
    credits_interview = Column(Integer, default=0)

    # AI assistant credits
    credits_assistant = Column(Integer, default=3)
    assistant_model = Column(String, default="gpt-4o-mini")

    # Subscription
    subscription_type = Column(String, default="free")
    subscription_expires = Column(DateTime, nullable=True)

    # Saved profile for repeat generations
    experience_text = Column(Text, nullable=True)
    education_text = Column(Text, nullable=True)
    skills_text = Column(Text, nullable=True)
    specialty = Column(String, nullable=True)   # job title / field, e.g. "Python Developer"

    # Referral
    referral_code = Column(String, nullable=True, unique=True)
    referred_by = Column(Integer, nullable=True)

    # Metadata
    total_resumes_generated = Column(Integer, default=0)
    total_assistant_messages = Column(Integer, default=0)
    total_spent_rub = Column(Float, default=0.0)
    checkin_sent_at = Column(DateTime, nullable=True)   # T+24h onboarding check-in
    language = Column(String, nullable=True, default='en')  # 'ru' | 'en' — user language preference
    email = Column(String, nullable=True)               # collected during onboarding for drip emails
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    amount_rub = Column(Float, nullable=False)
    package = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, succeeded, failed
    payment_id = Column(String, nullable=True)   # ID from ЮKassa
    created_at = Column(DateTime, default=datetime.utcnow)


class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    type = Column(String, nullable=False)  # resume, cover_letter, interview, analysis, assistant
    input_text = Column(Text, nullable=True)
    result_text = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class AssistantConversation(Base):
    """Conversation history for AI assistant context."""
    __tablename__ = "assistant_conversations"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    role = Column(String, nullable=False)       # "user" or "assistant"
    content = Column(Text, nullable=False)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False, index=True)
    job_title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    job_board = Column(String, nullable=True)
    job_url = Column(String, nullable=True)
    status = Column(String, default="applied")  # applied | response | interviewing | offer | rejected
    notes = Column(Text, nullable=True)
    applied_at = Column(DateTime, default=datetime.utcnow)
