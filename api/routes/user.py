from fastapi import APIRouter, Depends
from api.middleware.auth import get_telegram_user
from api.schemas import UserResponse
from database.db import get_or_create_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user(tg_user: dict = Depends(get_telegram_user)):
    user = await get_or_create_user(
        telegram_id=tg_user["id"],
        username=tg_user.get("username"),
        full_name=f"{tg_user.get('first_name', '')} {tg_user.get('last_name', '')}".strip(),
    )
    return UserResponse(
        telegram_id=user.telegram_id,
        username=user.username,
        full_name=user.full_name,
        credits_resume=user.credits_resume,
        credits_cover_letter=user.credits_cover_letter,
        credits_interview=user.credits_interview,
        credits_assistant=user.credits_assistant,
        subscription_type=user.subscription_type,
        total_resumes_generated=user.total_resumes_generated,
        total_assistant_messages=user.total_assistant_messages,
        total_spent_rub=user.total_spent_rub,
        referral_code=user.referral_code,
    )
