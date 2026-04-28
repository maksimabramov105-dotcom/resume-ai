from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from database.db import get_or_create_user, get_application_stats

router = Router()

_TRACKER_URL = "https://resumeai-bot.ru/app/tracker"


def _tracker_kb(lang: str) -> InlineKeyboardMarkup:
    label = "Открыть трекер →" if lang == "ru" else "View full tracker →"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, url=_TRACKER_URL)]
    ])


def _tracker_text(lang: str, s: dict) -> str:
    rate = s["response_rate"]
    if lang == "ru":
        return (
            "📊 <b>Ваши отклики</b>\n\n"
            f"Отправлено: <b>{s['total']}</b>\n"
            f"Получено ответов: <b>{s['responses']}</b>\n"
            f"На интервью: <b>{s['interviewing']}</b>\n"
            f"Оферы: 🎉 <b>{s['offers']}</b>\n"
            f"Отказы: <b>{s['rejected']}</b>\n\n"
            f"Конверсия в ответ: <b>{rate:.1f}%</b>\n\n"
            "Продолжайте — большинство соискателей получают первый ответ после 20–50 откликов."
        )
    return (
        "📊 <b>Your Applications</b>\n\n"
        f"Applied: <b>{s['total']}</b>\n"
        f"Responses received: <b>{s['responses']}</b>\n"
        f"Currently interviewing: <b>{s['interviewing']}</b>\n"
        f"Offers: 🎉 <b>{s['offers']}</b>\n"
        f"Rejected: <b>{s['rejected']}</b>\n\n"
        f"Your response rate: <b>{rate:.1f}%</b>\n\n"
        "Keep going — most people get their first response after 20–50 applications."
    )


@router.message(Command("tracker"))
async def cmd_tracker(message: Message) -> None:
    user = await get_or_create_user(message.from_user.id)
    lang = user.language or "ru"
    stats = await get_application_stats(message.from_user.id)

    try:
        from bot.analytics import track
        track(message.from_user.id, "tracker_viewed", {"total_applied": stats["total"]})
    except Exception:
        pass

    await message.answer(
        _tracker_text(lang, stats),
        parse_mode="HTML",
        reply_markup=_tracker_kb(lang),
    )
