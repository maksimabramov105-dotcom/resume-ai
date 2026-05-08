START_MESSAGE = """
👋 <b>Привет! Я — РезюмеАИ</b>

Твой личный AI-карьерный консультант. Шансы найти работу с нами — <b>100%</b>.

<b>Что я умею:</b>
📄 <b>Резюме</b> — под конкретную вакансию за 30 сек, без клише
✉️ <b>Сопроводительное письмо</b> — цепляющее, персонализированное
🎯 <b>Собеседование</b> — оцениваю ответы по методу STAR, указываю на слабые места
🔍 <b>Анализ вакансии</b> — зарплатная вилка, красные флаги, ATS-ключи
💬 <b>AI-ассистент</b> — любые вопросы по карьере 24/7

<b>Бонусы:</b>
🧠 Запоминаю твой профиль — второе резюме в 1 клик
📬 Еженедельный карьерный дайджест каждый понедельник
🎁 Приглашай друзей — получай бесплатные резюме

<b>Тебе уже доступно бесплатно:</b>
• 1 резюме  •  1 письмо  •  3 AI-сообщения

👇 <b>Выбери, с чего начать:</b>
"""

BOT_DESCRIPTION = (
    "🎯 Your personal AI career coach. Land your dream job faster.\n\n"
    "✅ Tailored resume in 30 seconds — no clichés, no templates\n"
    "✅ Remembers your profile — second resume in one click\n"
    "✅ Mock interview with STAR-method scoring\n"
    "✅ Vacancy analysis: salary, red flags, ATS keywords\n"
    "✅ Auto-apply to 4 international job boards\n"
    "✅ AI assistant 24/7\n\n"
    "Press START — first resume is free."
)

BOT_DESCRIPTION_RU = (
    "🎯 Твой личный AI-карьерный консультант. Шансы найти работу с нами — 100%.\n\n"
    "✅ Резюме под вакансию — 30 секунд, без клише и шаблонов\n"
    "✅ Запоминает профиль — второе резюме в 1 клик\n"
    "✅ Собеседование с оценкой по методу STAR\n"
    "✅ Анализ вакансии: зарплата, красные флаги, ATS-ключи\n"
    "✅ Автооткли на международные вакансии\n"
    "✅ AI-ассистент 24/7\n\n"
    "Нажми НАЧАТЬ — первое резюме бесплатно."
)

# Max 120 characters
BOT_SHORT_DESCRIPTION = (
    "AI-powered resume builder, mock interviews & auto-apply. "
    "Land your next job faster."
)

BOT_SHORT_DESCRIPTION_RU = (
    "Бот, который поможет зарабатывать на достойной работе. "
    "AI-резюме, собесы, карьерный рост — всё здесь."
)

RESUME_ASK_VACANCY = "📋 Отправьте <b>текст вакансии</b> (скопируйте с LinkedIn, Indeed или другого сайта):"
RESUME_ASK_EXPERIENCE = "💼 Расскажите о своём <b>опыте работы</b> (кратко, ключевые места и достижения):"
RESUME_ASK_EDUCATION = "🎓 <b>Образование</b> (ВУЗ, специальность, год окончания):"
RESUME_ASK_SKILLS = "🛠 <b>Ключевые навыки</b> (через запятую):"
RESUME_GENERATING = "⏳ Создаю идеальное резюме под эту вакансию..."
RESUME_NO_CREDITS = "У вас закончились кредиты на генерацию резюме.\n\nПополни баланс:"

COVER_LETTER_ASK_VACANCY = "📋 Отправьте <b>текст вакансии</b> для сопроводительного письма:"
COVER_LETTER_GENERATING = "⏳ Пишу сопроводительное письмо..."
COVER_LETTER_NO_CREDITS = "У вас закончились кредиты на сопроводительные письма.\n\nПополни баланс:"

INTERVIEW_ASK_VACANCY = "📋 Отправьте <b>текст вакансии</b>, на которую готовитесь:"
INTERVIEW_STARTING = "⏳ Начинаю собеседование..."
INTERVIEW_NO_CREDITS = "Симуляция собеседования — платная функция.\n\nПополни баланс:"
INTERVIEW_FINISH_PROMPT = "⏳ Подвожу итоги собеседования..."

VACANCY_ASK = "📋 Вставьте <b>текст вакансии</b> для анализа:"
VACANCY_ANALYZING = "🔍 Анализирую вакансию..."

NO_CREDITS_GENERIC = "У вас недостаточно кредитов.\n\nПополни баланс:"

BUY_MESSAGE = """💳 <b>Выбери пакет:</b>

📄 <b>ПАКЕТЫ РЕЗЮМЕ + ВСЁ:</b>
• Базовый — 299₽: 3 резюме + 3 письма + 1 собес + 10 AI
• Про — 790₽: 10 резюме + 10 писем + 5 собесов + 50 AI
• VIP 30 дней — 1990₽: безлимит на всё

💬 <b>ПАКЕТЫ AI-АССИСТЕНТА:</b>
• 50 сообщений — 149₽
• 200 сообщений — 399₽
• Безлимит 30 дней — 690₽
"""

PROFILE_MESSAGE = """👤 <b>Твой профиль:</b>
Имя: {full_name}
Подписка: {subscription_type}

💰 <b>Баланс:</b>
📄 Резюме: {credits_resume}
✉️ Письма: {credits_cover_letter}
🎯 Собесы: {credits_interview}
💬 AI-сообщения: {credits_assistant}

📊 <b>Статистика:</b>
Резюме создано: {total_resumes_generated}
AI-сообщений отправлено: {total_assistant_messages}
Потрачено: {total_spent_rub}₽
"""

REFERRAL_MESSAGE = """🎁 <b>Реферальная программа</b>

Пригласи друга и получи <b>3 бесплатных сообщения AI-ассистента!</b>

Твоя ссылка:
<code>https://t.me/{bot_username}?start=ref_{referral_code}</code>

Приглашено друзей: {referral_count}
"""

ASSISTANT_INTRO = """💬 <b>AI-ассистент активирован!</b>

Задай мне любой вопрос — я помогу с карьерой, текстами,
обучением и чем угодно ещё.

💰 Осталось сообщений: <b>{credits_assistant}</b>

Для выхода нажми кнопку ниже.
"""

ASSISTANT_NO_CREDITS = """💬 У тебя закончились сообщения AI-ассистента.

Докупи ещё:"""

ASSISTANT_LOW_CREDITS = "\n\n⚠️ <i>Осталось {n} сообщений.</i>"
ASSISTANT_LAST_MESSAGE = "\n\n❌ <i>Это было последнее сообщение.</i>"

PAYMENT_SUCCESS = "✅ Оплата подтверждена! Пакет «{name}» активирован.\nВаш баланс обновлён."
PAYMENT_CHECK_PENDING = (
    "⏳ <b>Платёж ещё не подтверждён.</b>\n\n"
    "Оплати через @CryptoBot и нажми кнопку ещё раз.\n"
    "Обычно занимает 1-2 минуты."
)
PAYMENT_NOT_FOUND = "Платёж не найден. Если оплата прошла — обратись в поддержку."

# Crypto
PAYMENT_CRYPTO_PENDING = (
    "💎 <b>Оплата криптовалютой (USDT)</b>\n\n"
    "Сумма: <b>{usdt} USDT</b>\n\n"
    "👉 Перейди по ссылке и оплати через @CryptoBot:\n"
    "{url}\n\n"
    "После оплаты нажми <b>Проверить оплату</b>."
)
PAYMENT_CRYPTO_CHECKING = "⏳ Проверяю..."

# Manual — RU Card
PAYMENT_MANUAL_RU = (
    "🇷🇺 <b>Перевод на карту РФ</b>\n\n"
    "Сумма: <b>{amount}₽</b>\n"
    "Банк: <b>{bank}</b>\n"
    "Номер карты:\n"
    "<code>{card}</code>\n"
    "Получатель: <b>{holder}</b>\n\n"
    "1. Переведи точную сумму\n"
    "2. Сделай скриншот подтверждения\n"
    "3. Нажми кнопку ниже и отправь скриншот"
)

# Manual — Revolut
PAYMENT_MANUAL_REVOLUT = (
    "💳 <b>Перевод на Revolut</b>\n\n"
    "Сумма: <b>{amount_rub}₽</b> (≈ <b>{amount_usdt} USDT</b>)\n"
    "Revolut: <b>{revolut}</b>\n\n"
    "1. Переведи сумму в любой валюте (RUB/EUR/GBP/USDT)\n"
    "2. Сделай скриншот подтверждения\n"
    "3. Нажми кнопку ниже и отправь скриншот"
)

PAYMENT_RECEIPT_ASK = "📸 Отправь скриншот подтверждения оплаты (фото):"
PAYMENT_RECEIPT_SENT = (
    "✅ Чек получен! Мы проверим оплату и зачислим кредиты в течение нескольких минут.\n\n"
    "Ожидай уведомления."
)
PAYMENT_RECEIPT_CHECKING = "🔍 Проверяю чек с помощью AI... Займёт несколько секунд."
PAYMENT_AUTO_APPROVED = (
    "✅ <b>Оплата подтверждена автоматически!</b>\n\n"
    "Пакет «{name}» активирован. Баланс обновлён. 🎉"
)

# Admin notifications
ADMIN_PAYMENT_NOTIFY = (
    "💰 <b>Новый платёж на проверку</b>\n\n"
    "Пользователь: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
    "Username: @{username}\n"
    "ID: <code>{user_id}</code>\n"
    "Пакет: {package}\n"
    "Сумма: {amount}₽\n"
    "Payment DB ID: {payment_db_id}"
)
ADMIN_PAYMENT_AI_ANALYSIS = (
    "\n\n🤖 <b>AI-анализ чека:</b>\n"
    "Вердикт: {verdict_emoji} {reason}\n"
    "Уверенность: {confidence}\n\n"
    "<i>{analysis}</i>"
)
ADMIN_PAYMENT_APPROVED = "✅ <b>ОДОБРЕНО</b>"
ADMIN_PAYMENT_REJECTED = "❌ <b>ОТКЛОНЕНО</b>"

PAYMENT_APPROVED_USER = "✅ Оплата подтверждена! Пакет «{name}» активирован. Баланс обновлён."
PAYMENT_REJECTED_USER = (
    "❌ Оплата не подтверждена.\n\n"
    "Если ты действительно оплатил — напиши в поддержку и приложи скриншот."
)

# Support
SUPPORT_MESSAGE = """🆘 <b>Поддержка РезюмеАИ</b>

Опиши свою проблему или задай вопрос — сообщение сразу попадёт к нам.

Можешь написать:
• Вопрос по оплате или балансу
• Проблему с генерацией
• Пожелание или идею
• Любой другой вопрос

👇 <b>Напиши сообщение прямо сейчас:</b>
"""

SUPPORT_SENT = (
    "✅ Сообщение отправлено в поддержку!\n\n"
    "Мы ответим тебе здесь в ближайшее время."
)

ADMIN_SUPPORT_NOTIFY = (
    "📩 <b>Новое обращение в поддержку</b>\n\n"
    "От: <a href='tg://user?id={user_id}'>{full_name}</a>\n"
    "Username: @{username}\n"
    "ID: <code>{user_id}</code>\n\n"
    "💬 <b>Сообщение:</b>\n{text}"
)
