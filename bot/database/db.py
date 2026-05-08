from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, delete, text
from contextlib import asynccontextmanager
import os
from typing import Optional

from models.user import Base, User, Payment, GenerationLog, AssistantConversation, Application

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./bot.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Migrations: add columns that may not exist in older DBs
    _migrations = [
        "ALTER TABLE users ADD COLUMN specialty VARCHAR",
        "ALTER TABLE users ADD COLUMN checkin_sent_at DATETIME",
        "ALTER TABLE users ADD COLUMN language VARCHAR DEFAULT 'en'",
        "ALTER TABLE users ADD COLUMN email VARCHAR",
        "ALTER TABLE users ADD COLUMN digest_sent_at DATETIME",
        "ALTER TABLE users ADD COLUMN digest_enabled INTEGER DEFAULT 1",
    ]
    for _sql in _migrations:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(_sql))
        except Exception:
            pass  # column already exists


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


async def get_application_stats(telegram_id: int) -> dict:
    from sqlalchemy import func
    async with get_session() as session:
        def _count(status_val=None):
            q = select(func.count()).select_from(Application).where(
                Application.telegram_id == telegram_id
            )
            if status_val:
                q = q.where(Application.status == status_val)
            return q

        total = (await session.execute(_count())).scalar() or 0
        responses = (await session.execute(_count("response"))).scalar() or 0
        interviewing = (await session.execute(_count("interviewing"))).scalar() or 0
        offers = (await session.execute(_count("offer"))).scalar() or 0
        rejected = (await session.execute(_count("rejected"))).scalar() or 0

    return {
        "total": total,
        "responses": responses,
        "interviewing": interviewing,
        "offers": offers,
        "rejected": rejected,
        "response_rate": (responses / total * 100) if total else 0.0,
    }


async def save_payment(
    telegram_id: int,
    package: str,
    payment_id: str = None,
    amount: float = 0.0,
    amount_rub: float = 0.0,  # kept for backward compat — not used
) -> Payment:
    async with get_session() as session:
        payment = Payment(
            telegram_id=telegram_id,
            amount_rub=amount,  # stores USD amount in the legacy column
            package=package,
            payment_id=payment_id,
            status="pending",
        )
        session.add(payment)
        await session.flush()
        await session.refresh(payment)
        return payment


async def update_user_digest_sent_at(telegram_id: int) -> None:
    """Record that we sent the daily digest to this user now."""
    from datetime import datetime
    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            user.digest_sent_at = datetime.utcnow()


async def update_user_digest_enabled(telegram_id: int, enabled: bool) -> None:
    """Enable or disable daily digest for a user."""
    async with get_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            user.digest_enabled = int(enabled)


async def update_payment_status(payment_id: str, status: str) -> Optional[Payment]:
    async with get_session() as session:
        result = await session.execute(
            select(Payment).where(Payment.payment_id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = status
        return payment
