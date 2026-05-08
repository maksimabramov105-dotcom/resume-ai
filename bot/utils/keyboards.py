from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from config import WEBAPP_URL
from utils.bot_translations import t


def main_menu_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=t(lang, 'menu.resume'),      callback_data="create_resume"),
            InlineKeyboardButton(text=t(lang, 'menu.cover_letter'),callback_data="cover_letter"),
        ],
        [
            InlineKeyboardButton(text=t(lang, 'menu.interview'),   callback_data="interview"),
            InlineKeyboardButton(text=t(lang, 'menu.vacancy'),     callback_data="vacancy_analysis"),
        ],
        [
            InlineKeyboardButton(text=t(lang, 'menu.assistant'),   callback_data="ai_assistant"),
        ],
        [
            InlineKeyboardButton(text=t(lang, 'menu.profile'),     callback_data="profile"),
            InlineKeyboardButton(text=t(lang, 'menu.buy'),         callback_data="buy_credits"),
        ],
        [
            InlineKeyboardButton(text=t(lang, 'menu.referral'),    callback_data="referral"),
        ],
        [
            InlineKeyboardButton(text=t(lang, 'menu.support'),     callback_data="support"),
        ],
        # Language toggle — always visible, shows the OTHER language to switch to
        [
            InlineKeyboardButton(
                text="🇬🇧 Switch to English" if lang == 'ru' else "🇷🇺 Переключить на Русский",
                callback_data="lang:en" if lang == 'ru' else "lang:ru",
            ),
        ],
    ]
    # Auto-apply link — opens web dashboard /app
    import os as _os
    _auto_url = _os.getenv("WEBAPP_BASE_URL", "https://resumeai-bot.ru").rstrip('/') + '/app'
    rows.insert(-1, [
        InlineKeyboardButton(text=t(lang, 'menu.auto_apply'), url=_auto_url),
    ])
    if WEBAPP_URL:
        rows.insert(0, [
            InlineKeyboardButton(text=t(lang, 'menu.webapp'), web_app=WebAppInfo(url=WEBAPP_URL)),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_resume_kb(
    bot_username: str = "topbestworkerbot",
    referral_code: str = "",
    lang: str = 'en',
) -> InlineKeyboardMarkup:
    import urllib.parse
    share_text = t(lang, 'share.text')
    share_url = (
        f"https://t.me/share/url"
        f"?url={urllib.parse.quote(f'https://t.me/{bot_username}?start=ref_{referral_code}', safe='')}"
        f"&text={urllib.parse.quote(share_text, safe='')}"
    )
    rows = [
        [
            InlineKeyboardButton(text=t(lang, 'btn.cover_for_job'),    callback_data="cover_letter"),
            InlineKeyboardButton(text=t(lang, 'btn.interview_for_job'),callback_data="interview"),
        ],
        [
            InlineKeyboardButton(text=t(lang, 'btn.new_resume'), callback_data="create_resume"),
            InlineKeyboardButton(text=t(lang, 'btn.menu'),       callback_data="main_menu"),
        ],
    ]
    if referral_code:
        rows.insert(0, [
            InlineKeyboardButton(text=t(lang, 'btn.share'), url=share_url)
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_cover_letter_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, 'btn.resume_for_job'), callback_data="create_resume"),
        ],
        [
            InlineKeyboardButton(text=t(lang, 'btn.menu'), callback_data="main_menu"),
        ],
    ])


def interview_kb(can_finish: bool = False, lang: str = 'en') -> InlineKeyboardMarkup:
    rows = []
    if can_finish:
        rows.append([
            InlineKeyboardButton(text=t(lang, 'interview.btn_finish'), callback_data="finish_interview"),
        ])
    rows.append([
        InlineKeyboardButton(text=t(lang, 'interview.btn_exit'), callback_data="exit_interview"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_interview_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, 'btn.repeat'),      callback_data="interview"),
            InlineKeyboardButton(text=t(lang, 'menu.resume'),     callback_data="create_resume"),
        ],
        [
            InlineKeyboardButton(text=t(lang, 'btn.ai_question'), callback_data="ai_assistant"),
            InlineKeyboardButton(text=t(lang, 'btn.menu'),        callback_data="main_menu"),
        ],
    ])


def after_vacancy_analysis_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, 'btn.resume_for_job'), callback_data="create_resume"),
        ],
        [
            InlineKeyboardButton(text=t(lang, 'btn.menu'), callback_data="main_menu"),
        ],
    ])


def assistant_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t(lang, 'btn.clear_history'), callback_data="clear_assistant_history"),
            InlineKeyboardButton(text=t(lang, 'btn.menu'),          callback_data="exit_assistant"),
        ],
    ])


def buy_credits_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'pay.basic'),        callback_data="buy_basic")],
        [InlineKeyboardButton(text=t(lang, 'pay.pro'),          callback_data="buy_pro")],
        [InlineKeyboardButton(text=t(lang, 'pay.vip'),          callback_data="buy_vip")],
        [InlineKeyboardButton(text=t(lang, 'pay.ai50'),         callback_data="buy_assistant_50")],
        [InlineKeyboardButton(text=t(lang, 'pay.ai200'),        callback_data="buy_assistant_200")],
        [InlineKeyboardButton(text=t(lang, 'pay.ai_unlimited'), callback_data="buy_assistant_unlimited")],
        [InlineKeyboardButton(text=t(lang, 'btn.menu'),         callback_data="main_menu")],
    ])


def buy_assistant_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'pay.ai50'),         callback_data="buy_assistant_50")],
        [InlineKeyboardButton(text=t(lang, 'pay.ai200'),        callback_data="buy_assistant_200")],
        [InlineKeyboardButton(text=t(lang, 'pay.ai_unlimited'), callback_data="buy_assistant_unlimited")],
        [InlineKeyboardButton(text=t(lang, 'btn.menu'),         callback_data="main_menu")],
    ])


def profile_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'btn.top_up'), callback_data="buy_credits")],
        [InlineKeyboardButton(text=t(lang, 'btn.menu'),   callback_data="main_menu")],
    ])


def payment_method_kb(package_key: str, lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'pay.method_crypto'),  callback_data=f"pay_method:{package_key}:crypto")],
        [InlineKeyboardButton(text=t(lang, 'pay.method_rucard'),  callback_data=f"pay_method:{package_key}:rucard")],
        [InlineKeyboardButton(text=t(lang, 'pay.method_revolut'), callback_data=f"pay_method:{package_key}:revolut")],
        [InlineKeyboardButton(text=t(lang, 'btn.back'),           callback_data="buy_credits")],
    ])


def crypto_check_kb(invoice_id: str, package_key: str, lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'pay.check'), callback_data=f"check_crypto:{invoice_id}:{package_key}")],
        [InlineKeyboardButton(text=t(lang, 'btn.menu'),  callback_data="main_menu")],
    ])


def manual_paid_kb(payment_db_id: int, lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'pay.i_paid'), callback_data=f"manual_paid:{payment_db_id}")],
        [InlineKeyboardButton(text=t(lang, 'btn.menu'),   callback_data="main_menu")],
    ])


def admin_approve_kb(payment_db_id: int, telegram_id: int, package_key: str) -> InlineKeyboardMarkup:
    """Admin-only keyboard — always in Russian."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"admin_ok:{payment_db_id}:{telegram_id}:{package_key}",
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"admin_no:{payment_db_id}:{telegram_id}:{package_key}",
            ),
        ],
    ])


def payment_check_kb(payment_id: str, lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'pay.check'), callback_data=f"check_payment:{payment_id}")],
        [InlineKeyboardButton(text=t(lang, 'btn.menu'),  callback_data="main_menu")],
    ])


def support_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'btn.menu'), callback_data="main_menu")],
    ])


def cancel_kb(lang: str = 'en') -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, 'btn.cancel'), callback_data="main_menu")],
    ])
