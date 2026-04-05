from fastapi import APIRouter, Depends
from api.middleware.auth import get_telegram_user
from api.schemas import VacancyAnalysisRequest, GenerationResponse
from services.openai_service import analyze_vacancy
from database.db import log_generation

router = APIRouter()


@router.post("/analyze", response_model=GenerationResponse)
async def api_analyze_vacancy(
    req: VacancyAnalysisRequest,
    tg_user: dict = Depends(get_telegram_user),
):
    # Free feature — no credits check
    text, tokens = await analyze_vacancy(req.vacancy_text)
    await log_generation(tg_user["id"], "analysis", req.vacancy_text, text, tokens)
    return GenerationResponse(text=text, tokens_used=tokens, credits_remaining=0)
