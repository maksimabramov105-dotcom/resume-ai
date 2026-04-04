from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import get_or_create_user, save_user, log_generation
from services.openai_service import generate_resume
from services.pdf_generator import ResumePDF
from utils.keyboards import after_resume_kb, buy_credits_kb, cancel_kb
from utils.texts import (
    RESUME_ASK_VACANCY, RESUME_ASK_EXPERIENCE, RESUME_ASK_EDUCATION,
    RESUME_ASK_SKILLS, RESUME_GENERATING, RESUME_NO_CREDITS,
)

router = Router()


class ResumeStates(StatesGroup):
    waiting_vacancy = State()
    waiting_experience = State()
    waiting_education = State()
    waiting_skills = State()


@router.callback_query(F.data == "create_resume")
async def start_resume(callback: CallbackQuery, state: FSMContext):
    user = await get_or_create_user(callback.from_user.id)
    if user.credits_resume <= 0:
        await callback.message.edit_text(RESUME_NO_CREDITS, reply_markup=buy_credits_kb())
        return
    await state.set_state(ResumeStates.waiting_vacancy)
    await callback.message.edit_text(RESUME_ASK_VACANCY, reply_markup=cancel_kb())


@router.message(ResumeStates.waiting_vacancy)
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
        await state.set_state(ResumeStates.waiting_experience)
        await message.answer(RESUME_ASK_EXPERIENCE, reply_markup=cancel_kb())


@router.message(ResumeStates.waiting_experience)
async def got_experience(message: Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await state.set_state(ResumeStates.waiting_education)
    await message.answer(RESUME_ASK_EDUCATION, reply_markup=cancel_kb())


@router.message(ResumeStates.waiting_education)
async def got_education(message: Message, state: FSMContext):
    await state.update_data(education=message.text)
    await state.set_state(ResumeStates.waiting_skills)
    await message.answer(RESUME_ASK_SKILLS, reply_markup=cancel_kb())


@router.message(ResumeStates.waiting_skills)
async def got_skills(message: Message, state: FSMContext):
    await state.update_data(skills=message.text)
    user = await get_or_create_user(message.from_user.id)
    await _generate_and_send(message, state, user)


async def _generate_and_send(message: Message, state: FSMContext, user):
    data = await state.get_data()
    await state.clear()

    status_msg = await message.answer(RESUME_GENERATING)

    resume_text, tokens = await generate_resume(
        vacancy=data.get("vacancy", ""),
        experience=data.get("experience", ""),
        education=data.get("education", ""),
        skills=data.get("skills", ""),
    )

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
    await status_msg.edit_text(
        f"📄 <b>Ваше резюме готово!</b>\n\n{text_preview}",
        reply_markup=after_resume_kb(),
    )

    # Generate and send PDF
    try:
        pdf = ResumePDF()
        pdf_bytes = pdf.generate(resume_text, user.full_name or "Резюме")
        await message.answer_document(
            BufferedInputFile(pdf_bytes, filename="resume.pdf"),
            caption="📄 Ваше резюме в формате PDF",
        )
    except Exception as e:
        await message.answer(f"⚠️ PDF не удалось создать: {e}")
