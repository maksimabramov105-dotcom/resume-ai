from fastapi import APIRouter, Depends, HTTPException
from api.middleware.auth import get_telegram_user
from api.schemas import CoverLetterRequest, GenerationResponse
from services.openai_service import generate_cover_letter
from database.db import get_or_create_user, save_user, log_generation

router = APIRouter()


@router.post("/generate", response_model=GenerationResponse)
async def api_generate_cover_letter(
    req: CoverLetterRequest,
    tg_user: dict = Depends(get_telegram_user),
):
    user = await get_or_create_user(tg_user["id"])
    if user.credits_cover_letter <= 0:
        raise HTTPException(status_code=402, detail="No cover letter credits remaining")

    candidate_summary = req.candidate_summary or ""
    if not candidate_summary and user.experience_text:
        parts = []
        if user.experience_text:
            parts.append(f"Опыт: {user.experience_text}")
        if user.skills_text:
            parts.append(f"Навыки: {user.skills_text}")
        candidate_summary = "\n".join(parts)

    text, tokens = await generate_cover_letter(req.vacancy_text, candidate_summary)

    user.credits_cover_letter -= 1
    await save_user(user)
    await log_generation(tg_user["id"], "cover_letter", req.vacancy_text, text, tokens)

    return GenerationResponse(text=text, tokens_used=tokens, credits_remaining=user.credits_cover_letter)
