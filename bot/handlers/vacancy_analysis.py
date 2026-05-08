from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_or_create_user, log_generation
from services.openai_service import analyze_vacancy
from utils.keyboards import after_vacancy_analysis_kb, cancel_kb
from utils.bot_translations import t

router = Router()


class VacancyAnalysisStates(StatesGroup):
    waiting_vacancy = State()


@router.callback_query(F.data == "vacancy_analysis")
async def start_analysis(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'en'
    await state.set_state(VacancyAnalysisStates.waiting_vacancy)
    await callback.message.edit_text(t(lang, 'vacancy.ask'), reply_markup=cancel_kb(lang))


@router.message(VacancyAnalysisStates.waiting_vacancy, F.text)
async def got_vacancy(message: Message, state: FSMContext):
    vacancy = message.text
    await state.clear()

    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'en'

    status_msg = await message.answer(t(lang, 'vacancy.analyzing'))

    analysis_text, tokens = await analyze_vacancy(vacancy)

    # Track feature usage for analytics (never raises)
    try:
        import sys, os as _os
        _ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        if _ROOT not in sys.path:
            sys.path.insert(0, _ROOT)
        from analytics_tracker import track_feature, DB_PATH as _ADB
        await track_feature(message.from_user.id, "vacancy_analysis", _ADB)
    except Exception:
        pass

    await log_generation(message.from_user.id, "analysis", vacancy, analysis_text, tokens)

    text_preview = analysis_text[:3800] if len(analysis_text) > 3800 else analysis_text
    from utils.md_cleaner import md_to_telegram
    clean_preview = md_to_telegram(text_preview)
    await status_msg.edit_text(
        f"{t(lang, 'vacancy.result')}\n\n{clean_preview}",
        reply_markup=after_vacancy_analysis_kb(lang),
    )


@router.message(VacancyAnalysisStates.waiting_vacancy)
async def vacancy_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'vacancy.wrong_type'))
