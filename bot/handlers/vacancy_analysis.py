from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_or_create_user, log_generation
from services.openai_service import analyze_vacancy
from utils.keyboards import after_vacancy_analysis_kb, cancel_kb
from utils.texts import VACANCY_ASK, VACANCY_ANALYZING

router = Router()


class VacancyAnalysisStates(StatesGroup):
    waiting_vacancy = State()


@router.callback_query(F.data == "vacancy_analysis")
async def start_analysis(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VacancyAnalysisStates.waiting_vacancy)
    await callback.message.edit_text(VACANCY_ASK, reply_markup=cancel_kb())


@router.message(VacancyAnalysisStates.waiting_vacancy)
async def got_vacancy(message: Message, state: FSMContext):
    vacancy = message.text
    await state.clear()

    status_msg = await message.answer(VACANCY_ANALYZING)

    analysis_text, tokens = await analyze_vacancy(vacancy)

    await log_generation(message.from_user.id, "analysis", vacancy, analysis_text, tokens)

    text_preview = analysis_text[:3800] if len(analysis_text) > 3800 else analysis_text
    from utils.md_cleaner import md_to_telegram
    clean_preview = md_to_telegram(text_preview)
    await status_msg.edit_text(
        f"🔍 <b>Анализ вакансии:</b>\n\n{clean_preview}",
        reply_markup=after_vacancy_analysis_kb(),
    )
