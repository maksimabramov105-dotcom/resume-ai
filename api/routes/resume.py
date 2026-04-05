from fastapi import APIRouter, Depends, HTTPException
from api.middleware.auth import get_telegram_user
from api.schemas import ResumeRequest, GenerationResponse
from services.openai_service import generate_resume
from database.db import get_or_create_user, save_user, log_generation

router = APIRouter()


@router.post("/generate", response_model=GenerationResponse)
async def api_generate_resume(
    req: ResumeRequest,
    tg_user: dict = Depends(get_telegram_user),
):
    user = await get_or_create_user(tg_user["id"])
    if user.credits_resume <= 0:
        raise HTTPException(status_code=402, detail="No resume credits remaining")

    text, tokens = await generate_resume(
        vacancy=req.vacancy_text,
        experience=req.experience,
        education=req.education,
        skills=req.skills,
    )

    user.credits_resume -= 1
    user.total_resumes_generated += 1
    user.experience_text = req.experience
    user.education_text = req.education
    user.skills_text = req.skills
    await save_user(user)
    await log_generation(tg_user["id"], "resume", req.vacancy_text, text, tokens)

    return GenerationResponse(text=text, tokens_used=tokens, credits_remaining=user.credits_resume)
