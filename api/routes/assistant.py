from fastapi import APIRouter, Depends, HTTPException
from api.middleware.auth import get_telegram_user
from api.schemas import AssistantMessageRequest, GenerationResponse
from services.openai_service import chat_completion
from database.db import get_or_create_user, save_user, get_conversation_history, save_conversation, log_generation
from prompts.assistant_prompt import ASSISTANT_SYSTEM_PROMPT
from config import ASSISTANT_MAX_CONTEXT_MESSAGES

router = APIRouter()


@router.post("/message", response_model=GenerationResponse)
async def api_assistant_message(
    req: AssistantMessageRequest,
    tg_user: dict = Depends(get_telegram_user),
):
    user = await get_or_create_user(tg_user["id"])
    if user.credits_assistant <= 0:
        raise HTTPException(status_code=402, detail="No assistant credits remaining")

    history = await get_conversation_history(tg_user["id"], limit=ASSISTANT_MAX_CONTEXT_MESSAGES)
    messages = [{"role": "system", "content": ASSISTANT_SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": req.message})

    response, tokens = await chat_completion(
        messages=messages,
        model=user.assistant_model or "gpt-4o-mini",
        max_tokens=800,
    )

    await save_conversation(tg_user["id"], "user", req.message, 0)
    await save_conversation(tg_user["id"], "assistant", response, tokens)

    user.credits_assistant -= 1
    user.total_assistant_messages += 1
    await save_user(user)
    await log_generation(tg_user["id"], "assistant", req.message, response, tokens)

    return GenerationResponse(text=response, tokens_used=tokens, credits_remaining=user.credits_assistant)


@router.delete("/history")
async def clear_history(tg_user: dict = Depends(get_telegram_user)):
    from database.db import clear_conversation_history
    await clear_conversation_history(tg_user["id"])
    return {"status": "cleared"}
