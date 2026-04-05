from fastapi import APIRouter, Depends, HTTPException
from api.middleware.auth import get_telegram_user
from api.schemas import InterviewStartRequest, InterviewAnswerRequest, GenerationResponse
from services.openai_service import start_interview, continue_interview, finish_interview
from database.db import get_or_create_user, save_user

router = APIRouter()


@router.post("/start", response_model=GenerationResponse)
async def api_start_interview(
    req: InterviewStartRequest,
    tg_user: dict = Depends(get_telegram_user),
):
    user = await get_or_create_user(tg_user["id"])
    if user.credits_interview <= 0:
        raise HTTPException(status_code=402, detail="No interview credits remaining")

    candidate_summary = req.candidate_summary or _build_summary(user)
    text, tokens = await start_interview(req.vacancy_text, candidate_summary)

    user.credits_interview -= 1
    await save_user(user)

    return GenerationResponse(text=text, tokens_used=tokens, credits_remaining=user.credits_interview)


@router.post("/answer", response_model=GenerationResponse)
async def api_interview_answer(
    req: InterviewAnswerRequest,
    tg_user: dict = Depends(get_telegram_user),
):
    text, tokens = await continue_interview(
        vacancy=req.vacancy_text,
        candidate_summary=req.candidate_summary or "",
        history=req.conversation_history,
        user_answer=req.answer,
    )
    return GenerationResponse(text=text, tokens_used=tokens, credits_remaining=0)


@router.post("/finish", response_model=GenerationResponse)
async def api_finish_interview(
    req: InterviewAnswerRequest,
    tg_user: dict = Depends(get_telegram_user),
):
    text, tokens = await finish_interview(
        vacancy=req.vacancy_text,
        candidate_summary=req.candidate_summary or "",
        history=req.conversation_history,
    )
    return GenerationResponse(text=text, tokens_used=tokens, credits_remaining=0)


def _build_summary(user) -> str:
    parts = []
    if user.experience_text:
        parts.append(f"Опыт: {user.experience_text}")
    if user.education_text:
        parts.append(f"Образование: {user.education_text}")
    if user.skills_text:
        parts.append(f"Навыки: {user.skills_text}")
    return "\n".join(parts) if parts else ""
