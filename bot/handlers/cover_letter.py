from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_or_create_user, save_user, log_generation
from services.openai_service import generate_cover_letter
from utils.md_cleaner import md_to_telegram
from utils.keyboards import after_cover_letter_kb, buy_credits_kb, cancel_kb
from utils.bot_translations import t

router = Router()


class CoverLetterStates(StatesGroup):
    waiting_vacancy = State()


@router.callback_query(F.data == "cover_letter")
async def start_cover_letter(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    if user.credits_cover_letter <= 0:
        await callback.message.edit_text(t(lang, 'cover.no_credits'), reply_markup=buy_credits_kb(lang))
        return
    await state.set_state(CoverLetterStates.waiting_vacancy)
    await callback.message.edit_text(t(lang, 'cover.ask_vacancy'), reply_markup=cancel_kb(lang))


@router.message(CoverLetterStates.waiting_vacancy, F.text)
async def got_vacancy(message: Message, state: FSMContext):
    vacancy = message.text
    await state.clear()

    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'ru'

    status_msg = await message.answer(t(lang, 'cover.generating'))

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
        from bot.utils.posthog_tracker import track as _ph_track
        _ph_track(message.from_user.id, 'cover_letter_generated', {'tokens': tokens})
    except Exception:
        pass

    user.credits_cover_letter -= 1
    await save_user(user)

    await log_generation(message.from_user.id, "cover_letter", vacancy, letter_text, tokens)

    text_preview = md_to_telegram(letter_text[:3800] if len(letter_text) > 3800 else letter_text)
    await status_msg.edit_text(
        f"{t(lang, 'cover.ready')}\n\n{text_preview}",
        parse_mode="HTML",
        reply_markup=after_cover_letter_kb(lang),
    )


@router.message(CoverLetterStates.waiting_vacancy)
async def cover_letter_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'cover.wrong_type'))
