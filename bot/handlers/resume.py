from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_or_create_user, save_user, log_generation
from services.openai_service import generate_resume
from services.pdf_generator import ResumePDF
from utils.keyboards import after_resume_kb, buy_credits_kb, cancel_kb
from utils.bot_translations import t

router = Router()


class ResumeStates(StatesGroup):
    waiting_vacancy = State()
    waiting_experience = State()
    waiting_education = State()
    waiting_skills = State()


@router.callback_query(F.data == "create_resume")
async def start_resume(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)
    lang = user.language or 'ru'
    if user.credits_resume <= 0:
        await callback.message.edit_text(t(lang, 'resume.no_credits'), reply_markup=buy_credits_kb(lang))
        return
    await state.set_state(ResumeStates.waiting_vacancy)
    await callback.message.edit_text(t(lang, 'resume.ask_vacancy'), reply_markup=cancel_kb(lang))


@router.message(ResumeStates.waiting_vacancy, F.text)
async def got_vacancy(message: Message, state: FSMContext):
    await state.update_data(vacancy=message.text)
    user = await get_or_create_user(message.from_user.id)

    # If user has saved profile, skip data collection
    if user.experience_text and user.education_text and user.skills_text:
        await state.update_data(
            experience=user.experience_text,
            education=user.education_text,
            skills=user.skills_text,
        )
        await _generate_and_send(message, state, user)
    else:
        lang = user.language or 'ru'
        await state.set_state(ResumeStates.waiting_experience)
        await message.answer(t(lang, 'resume.ask_experience'), reply_markup=cancel_kb(lang))


@router.message(ResumeStates.waiting_vacancy)
async def resume_vacancy_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'resume.wrong_type'))


@router.message(ResumeStates.waiting_experience, F.text)
async def got_experience(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'ru'
    await state.set_state(ResumeStates.waiting_education)
    await message.answer(t(lang, 'resume.ask_education'), reply_markup=cancel_kb(lang))


@router.message(ResumeStates.waiting_experience)
async def resume_experience_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'resume.wrong_exp'))


@router.message(ResumeStates.waiting_education, F.text)
async def got_education(message: Message, state: FSMContext):
    await state.update_data(education=message.text)
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or 'ru'
    await state.set_state(ResumeStates.waiting_skills)
    await message.answer(t(lang, 'resume.ask_skills'), reply_markup=cancel_kb(lang))


@router.message(ResumeStates.waiting_education)
async def resume_education_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'resume.wrong_edu'))


@router.message(ResumeStates.waiting_skills, F.text)
async def got_skills(message: Message, state: FSMContext):
    await state.update_data(skills=message.text)
    user = await get_or_create_user(message.from_user.id)
    await _generate_and_send(message, state, user)


@router.message(ResumeStates.waiting_skills)
async def resume_skills_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    await message.answer(t(user.language, 'resume.wrong_skills'))


async def _generate_and_send(message: Message, state: FSMContext, user):
    lang = user.language or 'ru'
    data = await state.get_data()
    await state.clear()

    status_msg = await message.answer(t(lang, 'resume.generating'))

    resume_text, tokens = await generate_resume(
        vacancy=data.get("vacancy", ""),
        experience=data.get("experience", ""),
        education=data.get("education", ""),
        skills=data.get("skills", ""),
    )

    # Track feature usage for analytics (never raises)
    try:
        import sys, os as _os
        _ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        if _ROOT not in sys.path:
            sys.path.insert(0, _ROOT)
        from analytics_tracker import track_feature, DB_PATH as _ADB
        await track_feature(message.from_user.id, "resume", _ADB)
        from bot.utils.posthog_tracker import track as _ph_track
        _ph_track(message.from_user.id, 'resume_completed', {'tokens': tokens})
    except Exception:
        pass

    # Deduct credit
    user.credits_resume -= 1
    user.total_resumes_generated += 1
    # Save profile for next time
    user.experience_text = data.get("experience", user.experience_text)
    user.education_text = data.get("education", user.education_text)
    user.skills_text = data.get("skills", user.skills_text)
    await save_user(user)

    await log_generation(message.from_user.id, "resume", data.get("vacancy", ""), resume_text, tokens)

    # Send text (truncate if too long for Telegram)
    text_preview = resume_text[:3800] if len(resume_text) > 3800 else resume_text
    from utils.md_cleaner import md_to_telegram
    clean_preview = md_to_telegram(text_preview)
    await status_msg.edit_text(
        f"{t(lang, 'resume.ready')}\n\n{clean_preview}",
        reply_markup=after_resume_kb(referral_code=user.referral_code or "", lang=lang),
    )

    # Generate and send PDF
    try:
        pdf = ResumePDF()
        pdf_bytes = pdf.generate(resume_text, user.full_name or "Resume")
        await message.answer_document(
            BufferedInputFile(pdf_bytes, filename="resume.pdf"),
            caption=t(lang, 'resume.pdf_caption'),
        )
    except Exception as e:
        await message.answer(t(lang, 'resume.pdf_error', error=e))
