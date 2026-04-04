from database.db import get_user, get_or_create_user, save_user
from models.user import User


async def get_or_create(telegram_id: int, username: str = None, full_name: str = None) -> User:
    return await get_or_create_user(telegram_id, username, full_name)


async def deduct_credits(user: User, feature: str) -> bool:
    """Deduct one credit for the given feature. Returns False if no credits left."""
    field = f"credits_{feature}"
    current = getattr(user, field, 0)
    if current <= 0:
        return False
    setattr(user, field, current - 1)
    await save_user(user)
    return True


async def has_credits(user: User, feature: str) -> bool:
    return getattr(user, f"credits_{feature}", 0) > 0


async def add_referral_bonus(referred_user: User):
    """Give bonus AI messages to a user who was referred."""
    referred_user.credits_assistant += 3
    await save_user(referred_user)
