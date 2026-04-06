from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from config import WEBAPP_URL


def main_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="📄 Создать резюме", callback_data="create_resume"),
            InlineKeyboardButton(text="✉️ Сопр. письмо", callback_data="cover_letter"),
        ],
        [
            InlineKeyboardButton(text="🎯 Симуляция собеса", callback_data="interview"),
            InlineKeyboardButton(text="🔍 Анализ вакансии", callback_data="vacancy_analysis"),
        ],
        [
            InlineKeyboardButton(text="💬 AI-ассистент", callback_data="ai_assistant"),
        ],
        [
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile"),
            InlineKeyboardButton(text="💳 Купить кредиты", callback_data="buy_credits"),
        ],
        [
            InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="referral"),
        ],
        [
            InlineKeyboardButton(text="🆘 Поддержка", callback_data="support"),
        ],
    ]
    if WEBAPP_URL:
        rows.insert(0, [
            InlineKeyboardButton(text="🌐 Открыть Mini App", web_app=WebAppInfo(url=WEBAPP_URL)),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_resume_kb(bot_username: str = "topbestworkerbot", referral_code: str = "") -> InlineKeyboardMarkup:
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}?start=ref_{referral_code}&text=Попробуй%20РезюмеАИ%20—%20резюме%20за%2030%20секунд%21"
    rows = [
        [
            InlineKeyboardButton(text="✉️ Письмо под эту вакансию", callback_data="cover_letter"),
            InlineKeyboardButton(text="🎯 Собес под эту вакансию", callback_data="interview"),
        ],
        [
            InlineKeyboardButton(text="📄 Новое резюме", callback_data="create_resume"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu"),
        ],
    ]
    if referral_code:
        rows.insert(0, [
            InlineKeyboardButton(
                text="🎁 Поделиться → получить бесплатное резюме",
                url=share_url,
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_cover_letter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Резюме под эту вакансию", callback_data="create_resume"),
        ],
        [
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu"),
        ],
    ])


def interview_kb(can_finish: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if can_finish:
        rows.append([
            InlineKeyboardButton(text="⏭ Завершить собеседование", callback_data="finish_interview"),
        ])
    rows.append([
        InlineKeyboardButton(text="🏠 Выйти из собеседования", callback_data="exit_interview"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def after_interview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔄 Ещё раз", callback_data="interview"),
            InlineKeyboardButton(text="📄 Создать резюме", callback_data="create_resume"),
        ],
        [
            InlineKeyboardButton(text="💬 Задать вопрос AI", callback_data="ai_assistant"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu"),
        ],
    ])


def after_vacancy_analysis_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Создать резюме под эту вакансию", callback_data="create_resume"),
        ],
        [
            InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu"),
        ],
    ])


def assistant_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear_assistant_history"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="exit_assistant"),
        ],
    ])


def buy_credits_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Базовый — 299₽", callback_data="buy_basic")],
        [InlineKeyboardButton(text="⭐ Про — 790₽", callback_data="buy_pro")],
        [InlineKeyboardButton(text="👑 VIP 30 дней — 1990₽", callback_data="buy_vip")],
        [InlineKeyboardButton(text="💬 50 сообщений AI — 149₽", callback_data="buy_assistant_50")],
        [InlineKeyboardButton(text="💬 200 сообщений AI — 399₽", callback_data="buy_assistant_200")],
        [InlineKeyboardButton(text="💬 AI Безлимит 30 дней — 690₽", callback_data="buy_assistant_unlimited")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")],
    ])


def buy_assistant_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 50 сообщений — 149₽", callback_data="buy_assistant_50")],
        [InlineKeyboardButton(text="💬 200 сообщений — 399₽", callback_data="buy_assistant_200")],
        [InlineKeyboardButton(text="💬 AI Безлимит 30 дней — 690₽", callback_data="buy_assistant_unlimited")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")],
    ])


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="buy_credits")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")],
    ])


def payment_method_kb(package_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Криптовалюта (USDT)", callback_data=f"pay_method:{package_key}:crypto")],
        [InlineKeyboardButton(text="🇷🇺 Карта РФ (перевод)", callback_data=f"pay_method:{package_key}:rucard")],
        [InlineKeyboardButton(text="💳 Revolut", callback_data=f"pay_method:{package_key}:revolut")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="buy_credits")],
    ])


def crypto_check_kb(invoice_id: str, package_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_crypto:{invoice_id}:{package_key}")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")],
    ])


def manual_paid_kb(payment_db_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил — отправить чек", callback_data=f"manual_paid:{payment_db_id}")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")],
    ])


def admin_approve_kb(payment_db_id: int, telegram_id: int, package_key: str) -> InlineKeyboardMarkup:
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


def payment_check_kb(payment_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment:{payment_id}")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")],
    ])


def support_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В меню", callback_data="main_menu")],
    ])


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")],
    ])
