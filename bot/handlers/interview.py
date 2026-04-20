from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_or_create_user, save_user, log_generation
from services.openai_service import start_interview, continue_interview, finish_interview
from utils.md_cleaner import md_to_telegram
from utils.keyboards import interview_kb, after_interview_kb, buy_credits_kb, cancel_kb, main_menu_kb
from utils.bot_translations import t

router = Router()

MIN_QUESTIONS_TO_FINISH = 5


class InterviewStates(StatesGroup):
    waiting_vacancy = State()
    active = State()


@router.callback_query(F.data == "interview")
async def start_interview_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    if user.credits_interview <= 0:
        await callback.message.edit_text(t(lang, 'interview.no_credits'), reply_markup=buy_credits_kb(lang))
        return
    await state.set_state(InterviewStates.waiting_vacancy)
    await callback.message.edit_text(t(lang, 'interview.ask_vacancy'), reply_markup=cancel_kb(lang))


@router.message(InterviewStates.waiting_vacancy, F.text)
async def got_vacancy(message: Message, state: FSMContext):
    vacancy = message.text
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'ru'

    candidate_summary = _build_candidate_summary(user)

    status_msg = await message.answer(t(lang, 'interview.starting'))

    first_question, tokens = await start_interview(vacancy, candidate_summary, lang=lang)

    history = [{"role": "assistant", "content": first_question}]
    await state.set_state(InterviewStates.active)
    await state.update_data(
        vacancy=vacancy,
        candidate_summary=candidate_summary,
        history=history,
        question_count=1,
    )

    # Deduct credit
    user.credits_interview -= 1
    await save_user(user)

    await status_msg.edit_text(
        f"{t(lang, 'interview.started')}\n\n{first_question}",
        reply_markup=interview_kb(can_finish=False, lang=lang),
    )


@router.message(InterviewStates.waiting_vacancy)
async def interview_vacancy_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'interview.wrong_vacancy'))


@router.message(InterviewStates.active, F.text)
async def handle_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    history = data.get("history", [])
    question_count = data.get("question_count", 1)
    vacancy = data.get("vacancy", "")
    candidate_summary = data.get("candidate_summary", "")

    history.append({"role": "user", "content": message.text})

    await message.chat.do("typing")

    user_for_lang = await get_or_create_user(message.from_user.id)
    _lang = user_for_lang.language or 'ru'
    response, tokens = await continue_interview(vacancy, candidate_summary, history, message.text, lang=_lang)
    history.append({"role": "assistant", "content": response})

    question_count += 1
    await state.update_data(history=history, question_count=question_count)

    can_finish = question_count >= MIN_QUESTIONS_TO_FINISH
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'ru'

    await message.answer(
        md_to_telegram(response),
        parse_mode="HTML",
        reply_markup=interview_kb(can_finish=can_finish, lang=lang),
    )


@router.callback_query(F.data == "finish_interview", InterviewStates.active)
async def finish_interview_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'

    data = await state.get_data()
    history = data.get("history", [])
    vacancy = data.get("vacancy", "")
    candidate_summary = data.get("candidate_summary", "")

    await callback.message.edit_text(t(lang, 'interview.finish_prompt'))

    try:
        final_text, tokens = await finish_interview(vacancy, candidate_summary, history, lang=lang)

        # Track feature usage for analytics (never raises)
        try:
            import sys, os as _os
            _ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
            if _ROOT not in sys.path:
                sys.path.insert(0, _ROOT)
            from analytics_tracker import track_feature, DB_PATH as _ADB
            await track_feature(callback.from_user.id, "interview", _ADB)
        except Exception:
            pass

    except Exception as e:
        await state.clear()
        await callback.message.answer(
            t(lang, 'interview.finish_error', error=e),
            reply_markup=after_interview_kb(lang),
        )
        return

    await state.clear()

    header = f"{t(lang, 'interview.finish_header')}\n\n"
    max_text_len = 4096 - len(header)
    if len(final_text) > max_text_len:
        final_text = final_text[:max_text_len - 1] + "…"

    await callback.message.answer(
        f"{header}{final_text}",
        reply_markup=after_interview_kb(lang),
    )

    await log_generation(callback.from_user.id, "interview", vacancy, final_text, tokens)


@router.message(InterviewStates.active)
async def interview_answer_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'interview.wrong_answer'))


@router.callback_query(F.data == "exit_interview")
async def exit_interview_handler(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    await callback.message.edit_text(t(lang, 'start.welcome'), reply_markup=main_menu_kb(lang))


def _build_candidate_summary(user) -> str:
    parts = []
    if user.experience_text:
        parts.append(f"Опыт: {user.experience_text}")
    if user.education_text:
        parts.append(f"Образование: {user.education_text}")
    if user.skills_text:
        parts.append(f"Навыки: {user.skills_text}")
    return "\n".join(parts) if parts else "Информация о кандидате не указана."
