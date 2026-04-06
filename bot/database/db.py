from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, delete, text
from contextlib import asynccontextmanager
import os
from typing import Optional

from models.user import Base, User, Payment, GenerationLog, AssistantConversation

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Migrate: add specialty column if missing
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE users ADD COLUMN specialty VARCHAR"))
    except Exception:
        pass  # Column already exists


@asynccontextmanager
async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_user(telegram_id: int) -> Optional[User]:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()


async def get_or_create_user(telegram_id: int, username: str = None, full_name: str = None) -> User:
    async with get_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            import secrets
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                referral_code=secrets.token_urlsafe(6),
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
        else:
            if username:
                user.username = username
            if full_name:
                user.full_name = full_name
            from datetime import datetime
            user.last_active = datetime.utcnow()
        return user


async def save_user(user: User):
    async with get_session() as session:
        await session.merge(user)
        await session.flush()


async def get_conversation_history(telegram_id: int, limit: int = 10):
    async with get_session() as session:
        result = await session.execute(
            select(AssistantConversation)
            .where(AssistantConversation.telegram_id == telegram_id)
            .order_by(AssistantConversation.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return list(reversed(rows))


async def save_conversation(telegram_id: int, role: str, content: str, tokens_used: int = 0):
    async with get_session() as session:
        entry = AssistantConversation(
            telegram_id=telegram_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
        )
        session.add(entry)


async def clear_conversation_history(telegram_id: int):
    async with get_session() as session:
        await session.execute(
            delete(AssistantConversation).where(
                AssistantConversation.telegram_id == telegram_id
            )
        )


async def get_all_users() -> list:
    """Return all users (for digest etc.)."""
    from models.user import User
    async with get_session() as session:
        result = await session.execute(select(User))
        return result.scalars().all()


async def log_generation(
    telegram_id: int,
    gen_type: str,
    input_text: str,
    result_text: str,
    tokens_used: int,
):
    cost_usd = tokens_used * 0.00000015  # gpt-4o-mini ~$0.15/1M tokens
    async with get_session() as session:
        entry = GenerationLog(
            telegram_id=telegram_id,
            type=gen_type,
            input_text=input_text[:2000] if input_text else None,
            result_text=result_text[:4000] if result_text else None,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )
        session.add(entry)


async def save_payment(telegram_id: int, amount_rub: float, package: str, payment_id: str = None) -> Payment:
    async with get_session() as session:
        payment = Payment(
            telegram_id=telegram_id,
            amount_rub=amount_rub,
            package=package,
            payment_id=payment_id,
            status="pending",
        )
        session.add(payment)
        await session.flush()
        await session.refresh(payment)
        return payment


async def update_payment_status(payment_id: str, status: str) -> Optional[Payment]:
    async with get_session() as session:
        result = await session.execute(
            select(Payment).where(Payment.payment_id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = status
        return payment
