import random

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import (
    get_or_create_user, save_user, log_generation,
    get_conversation_history, save_conversation, clear_conversation_history,
)
from services.openai_service import chat_completion
from prompts.assistant_prompt import ASSISTANT_SYSTEM_PROMPT, ASSISTANT_UPSELL_MESSAGES
from utils.keyboards import assistant_kb, buy_assistant_kb, main_menu_kb
from utils.texts import (
    ASSISTANT_INTRO, ASSISTANT_NO_CREDITS, ASSISTANT_LOW_CREDITS, ASSISTANT_LAST_MESSAGE,
)
from config import ASSISTANT_MAX_CONTEXT_MESSAGES

router = Router()


class AssistantStates(StatesGroup):
    active = State()


@router.callback_query(F.data == "ai_assistant")
async def start_assistant(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)

    if user.credits_assistant <= 0:
        await callback.message.edit_text(ASSISTANT_NO_CREDITS, reply_markup=buy_assistant_kb())
        return

    await state.set_state(AssistantStates.active)
    await state.update_data(message_count=0)

    await callback.message.edit_text(
        ASSISTANT_INTRO.format(credits_assistant=user.credits_assistant),
        reply_markup=assistant_kb(),
    )


@router.message(AssistantStates.active, F.text)
async def handle_assistant_message(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)

    if user.credits_assistant <= 0:
        await message.answer(ASSISTANT_NO_CREDITS, reply_markup=buy_assistant_kb())
        await state.clear()
        return

    history = await get_conversation_history(message.from_user.id, limit=ASSISTANT_MAX_CONTEXT_MESSAGES)

    messages = [{"role": "system", "content": ASSISTANT_SYSTEM_PROMPT}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": message.text})

    await message.chat.do("typing")

    response, tokens = await chat_completion(
        messages=messages,
        model=user.assistant_model or "gpt-4o-mini",
        max_tokens=800,
    )

    # Track feature usage for analytics (never raises)
    try:
        import sys, os as _os
        _ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        if _ROOT not in sys.path:
            sys.path.insert(0, _ROOT)
        from analytics_tracker import track_feature, DB_PATH as _ADB
        await track_feature(message.from_user.id, "ai_message", _ADB)
    except Exception:
        pass

    # Save to conversation history
    await save_conversation(message.from_user.id, "user", message.text, 0)
    await save_conversation(message.from_user.id, "assistant", response, tokens)

    # Deduct credit
    user.credits_assistant -= 1
    user.total_assistant_messages += 1
    await save_user(user)

    await log_generation(message.from_user.id, "assistant", message.text, response, tokens)

    # Upsell every 3rd message
    data = await state.get_data()
    msg_count = data.get("message_count", 0) + 1
    await state.update_data(message_count=msg_count)

    upsell = random.choice(ASSISTANT_UPSELL_MESSAGES) if msg_count % 3 == 0 else ""

    warning = ""
    if user.credits_assistant == 5:
        warning = ASSISTANT_LOW_CREDITS.format(n=5)
    elif user.credits_assistant == 0:
        warning = ASSISTANT_LAST_MESSAGE

    full_text = f"{response}{upsell}{warning}"
    if len(full_text) > 4096:
        full_text = full_text[:4093] + "…"
    await message.answer(full_text, reply_markup=assistant_kb())


@router.message(AssistantStates.active)
async def assistant_wrong_type(message: Message):
    await message.answer("💬 Пожалуйста, напиши свой вопрос текстом.")


@router.callback_query(F.data == "clear_assistant_history")
async def clear_history(callback: CallbackQuery):
    await clear_conversation_history(callback.from_user.id)
    await callback.answer("История очищена ✅")


@router.callback_query(F.data == "exit_assistant")
async def exit_assistant(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    from utils.texts import START_MESSAGE
    await callback.message.edit_text(START_MESSAGE, reply_markup=main_menu_kb())
