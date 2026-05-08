"""
resume_tailor.py — Bot handler for on-demand per-job resume tailoring.

User flow:
  1. /tailor command (or "tailor_resume" menu callback)
  2. Bot asks for a job posting URL or description text
  3. User sends job text
  4. Bot calls the autoapply API (POST /api/resume/tailor)
  5. Bot replies with a tailored resume as a text file or inline message

Requires the user to have:
  - A Telegram → AutoApply linked account (autoapply_token in bot DB)
  - A resume stored in their AutoApply profile
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from database.db import get_or_create_user
from utils.bot_translations import t
from utils.keyboards import main_menu_kb, cancel_kb

router = Router()

_MAX_JOB_TEXT = 5000  # chars; truncate before sending to API


class TailorStates(StatesGroup):
    waiting_job_text = State()


@router.message(Command("tailor"))
@router.callback_query(F.data == "tailor_resume")
async def tailor_start(update: Message | CallbackQuery, state: FSMContext):
    user = await get_or_create_user(
        update.from_user.id if isinstance(update, Message) else update.from_user.id
    )
    lang = user.language or "en"

    if lang == "en":
        text = (
            "✏️ <b>Resume Tailoring</b>\n\n"
            "Send me the job description (copy-paste from LinkedIn, Indeed, etc.).\n"
            "I'll produce a version of your resume tailored to this specific role."
        )
    else:
        text = (
            "✏️ <b>Адаптация резюме под вакансию</b>\n\n"
            "Отправьте текст вакансии (скопируйте с LinkedIn, hh.ru и т.д.).\n"
            "Я создам версию вашего резюме, адаптированную под эту роль."
        )

    await state.set_state(TailorStates.waiting_job_text)

    if isinstance(update, Message):
        await update.answer(text, reply_markup=cancel_kb(lang))
    else:
        await update.answer()
        await update.message.edit_text(text, reply_markup=cancel_kb(lang))


@router.message(TailorStates.waiting_job_text, F.text)
async def got_job_text(message: Message, state: FSMContext):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or "en"
    await state.clear()

    job_text = (message.text or "").strip()
    if len(job_text) < 20:
        await message.answer(
            "Please send a longer job description (at least a few lines)."
            if lang == "en"
            else "Текст вакансии слишком короткий. Отправьте более подробное описание.",
            reply_markup=main_menu_kb(lang),
        )
        return

    thinking = await message.answer(
        "⏳ Tailoring your resume… (this takes ~15 seconds)"
        if lang == "en"
        else "⏳ Адаптирую резюме… (~15 секунд)"
    )

    try:
        import os, aiohttp as _aiohttp, json as _json

        autoapply_base = os.getenv("WEBAPP_BASE_URL", "https://resumeai-bot.ru")

        # Retrieve the user's AutoApply JWT (stored in bot DB via autoapply_token column)
        autoapply_token = getattr(user, "autoapply_token", None) or ""
        if not autoapply_token:
            await thinking.delete()
            await message.answer(
                "🔗 Your bot account is not linked to AutoApply yet.\n"
                "Use /start → Dashboard → Link Telegram to connect."
                if lang == "en"
                else "🔗 Ваш аккаунт не связан с AutoApply.\n"
                "Перейдите в /start → Кабинет → Привязать Telegram.",
                reply_markup=main_menu_kb(lang),
            )
            return

        payload = {
            "job_description": job_text[:_MAX_JOB_TEXT],
        }
        headers = {
            "Authorization": f"Bearer {autoapply_token}",
            "Content-Type": "application/json",
        }

        async with _aiohttp.ClientSession() as session:
            async with session.post(
                f"{autoapply_base}/api/resume/tailor",
                json=payload,
                headers=headers,
                timeout=_aiohttp.ClientTimeout(total=50),
            ) as resp:
                if resp.status == 400:
                    err = await resp.json()
                    await thinking.delete()
                    await message.answer(
                        f"❌ {err.get('detail', 'Bad request')}",
                        reply_markup=main_menu_kb(lang),
                    )
                    return
                if resp.status != 200:
                    raise RuntimeError(f"API {resp.status}")
                data = await resp.json()

        tailored = data.get("tailored_resume", "")
        job_title = data.get("job_title", "")

        await thinking.delete()

        if not tailored:
            await message.answer(
                "❌ Could not generate tailored resume. Please try again."
                if lang == "en"
                else "❌ Не удалось создать адаптированное резюме. Попробуйте снова.",
                reply_markup=main_menu_kb(lang),
            )
            return

        # Send as a .txt file for easy copy-paste
        filename = f"resume_tailored_{job_title[:30].replace(' ', '_') or 'job'}.txt"
        file = BufferedInputFile(tailored.encode("utf-8"), filename=filename)

        caption = (
            f"✅ <b>Tailored resume</b> for <i>{job_title or 'this role'}</i>\n\n"
            "Download and use directly or paste into your profile."
            if lang == "en"
            else f"✅ <b>Адаптированное резюме</b> для <i>{job_title or 'вакансии'}</i>\n\n"
            "Скачайте и используйте или скопируйте в профиль."
        )

        await message.answer_document(file, caption=caption, reply_markup=main_menu_kb(lang))

        try:
            from bot.analytics import track as _ph_track
            _ph_track(message.from_user.id, "resume_tailored", {"has_job_title": bool(job_title)})
        except Exception:
            pass

    except Exception as exc:
        await thinking.delete()
        await message.answer(
            f"❌ Error: {exc}\nPlease try again later."
            if lang == "en"
            else f"❌ Ошибка: {exc}\nПопробуйте позже.",
            reply_markup=main_menu_kb(lang),
        )


@router.message(TailorStates.waiting_job_text)
async def tailor_wrong_type(message: Message):
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or "en"
    await message.answer(
        "Please send the job description as text." if lang == "en"
        else "Отправьте текст вакансии сообщением."
    )
