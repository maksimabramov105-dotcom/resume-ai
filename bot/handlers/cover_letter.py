from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_or_create_user, save_user, log_generation
from services.openai_service import generate_cover_letter
from utils.keyboards import after_cover_letter_kb, buy_credits_kb, cancel_kb
from utils.texts import (
    COVER_LETTER_ASK_VACANCY, COVER_LETTER_GENERATING, COVER_LETTER_NO_CREDITS,
)

router = Router()


class CoverLetterStates(StatesGroup):
    waiting_vacancy = State()


@router.callback_query(F.data == "cover_letter")
async def start_cover_letter(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)
    if user.credits_cover_letter <= 0:
        await callback.message.edit_text(COVER_LETTER_NO_CREDITS, reply_markup=buy_credits_kb())
        return
    await state.set_state(CoverLetterStates.waiting_vacancy)
    await callback.message.edit_text(COVER_LETTER_ASK_VACANCY, reply_markup=cancel_kb())


@router.message(CoverLetterStates.waiting_vacancy, F.text)
async def got_vacancy(message: Message, state: FSMContext):
    vacancy = message.text
    await state.clear()

    user = await get_or_create_user(message.from_user.id)

    status_msg = await message.answer(COVER_LETTER_GENERATING)

    candidate_summary = ""
    if user.experience_text:
        candidate_summary += f"Опыт: {user.experience_text}\n"
    if user.education_text:
        candidate_summary += f"Образование: {user.education_text}\n"
    if user.skills_text:
        candidate_summary += f"Навыки: {user.skills_text}"

    if not candidate_summary:
        candidate_summary = "Информация о кандидате не указана. Напиши общее письмо."

    letter_text, tokens = await generate_cover_letter(vacancy, candidate_summary)

    # Track feature usage for analytics (never raises)
    try:
        import sys, os as _os
        _ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        if _ROOT not in sys.path:
            sys.path.insert(0, _ROOT)
        from analytics_tracker import track_feature, DB_PATH as _ADB
        await track_feature(message.from_user.id, "cover_letter", _ADB)
    except Exception:
        pass

    user.credits_cover_letter -= 1
    await save_user(user)

    await log_generation(message.from_user.id, "cover_letter", vacancy, letter_text, tokens)

    text_preview = letter_text[:3800] if len(letter_text) > 3800 else letter_text
    await status_msg.edit_text(
        f"✉️ <b>Сопроводительное письмо готово!</b>\n\n{text_preview}",
        reply_markup=after_cover_letter_kb(),
    )


@router.message(CoverLetterStates.waiting_vacancy)
async def cover_letter_wrong_type(message: Message):
    await message.answer("📋 Пожалуйста, напиши текст вакансии.")
