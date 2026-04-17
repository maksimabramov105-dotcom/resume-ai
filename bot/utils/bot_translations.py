"""
Bilingual string lookup for the ResumeAI Telegram bot.

Usage:
    from utils.bot_translations import t
    text = t(user.language, 'start.welcome')
    text = t(user.language, 'resume.pdf_error', error="timeout")
"""
from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    # ────────────────────────────────────────────────────────────────────────
    'ru': {
        # Start / Welcome
        'start.welcome': (
            "👋 <b>Привет! Я — РезюмеАИ</b>\n\n"
            "Твой личный AI-карьерный консультант. Шансы найти работу с нами — <b>100%</b>.\n\n"
            "<b>Что я умею:</b>\n"
            "📄 <b>Резюме</b> — под конкретную вакансию за 30 сек, без клише\n"
            "✉️ <b>Сопроводительное письмо</b> — цепляющее, персонализированное\n"
            "🎯 <b>Собеседование</b> — оцениваю ответы по методу STAR, указываю на слабые места\n"
            "🔍 <b>Анализ вакансии</b> — зарплатная вилка, красные флаги, ATS-ключи\n"
            "💬 <b>AI-ассистент</b> — любые вопросы по карьере 24/7\n\n"
            "<b>Бонусы:</b>\n"
            "🧠 Запоминаю твой профиль — второе резюме в 1 клик\n"
            "📬 Еженедельный карьерный дайджест каждый понедельник\n"
            "🎁 Приглашай друзей — получай бесплатные резюме\n\n"
            "<b>Тебе уже доступно бесплатно:</b>\n"
            "• 1 резюме  •  1 письмо  •  3 AI-сообщения\n\n"
            "👇 <b>Выбери, с чего начать:</b>"
        ),
        'start.choose_lang': "👋 Привет! Выбери язык / Choose your language:",
        'start.lang_set': "✅ Язык установлен: <b>Русский</b>\n\nДобро пожаловать! 👇",

        # Language
        'lang.choose': "🌐 Выбери язык / Choose your language:",
        'lang.set_ru': "✅ Язык: <b>Русский</b>",
        'lang.set_en': "✅ Language: <b>English</b>",

        # Menu buttons
        'menu.resume':      "📄 Создать резюме",
        'menu.cover_letter':"✉️ Сопр. письмо",
        'menu.interview':   "🎯 Симуляция собеса",
        'menu.vacancy':     "🔍 Анализ вакансии",
        'menu.assistant':   "💬 AI-ассистент",
        'menu.profile':     "👤 Мой профиль",
        'menu.buy':         "💳 Купить кредиты",
        'menu.referral':    "🎁 Пригласить друга",
        'menu.support':     "🆘 Поддержка",
        'menu.webapp':      "🌐 Открыть Mini App",

        # Common buttons
        'btn.menu':            "🏠 В меню",
        'btn.cancel':          "❌ Отмена",
        'btn.back':            "◀️ Назад",
        'btn.resume_for_job':  "📄 Создать резюме под эту вакансию",
        'btn.cover_for_job':   "✉️ Письмо под эту вакансию",
        'btn.interview_for_job':"🎯 Собес под эту вакансию",
        'btn.new_resume':      "📄 Новое резюме",
        'btn.repeat':          "🔄 Ещё раз",
        'btn.ai_question':     "💬 Задать вопрос AI",
        'btn.clear_history':   "🗑 Очистить историю",
        'btn.share':           "🎁 Поделиться → получить бесплатное резюме",
        'btn.top_up':          "💳 Пополнить баланс",

        # Resume flow
        'resume.ask_vacancy':  "📋 Отправьте <b>текст вакансии</b> (скопируйте с hh.ru или другого сайта):",
        'resume.ask_experience':"💼 Расскажите о своём <b>опыте работы</b> (кратко, ключевые места и достижения):",
        'resume.ask_education':"🎓 <b>Образование</b> (ВУЗ, специальность, год окончания):",
        'resume.ask_skills':   "🛠 <b>Ключевые навыки</b> (через запятую):",
        'resume.generating':   "⏳ Создаю идеальное резюме под эту вакансию...",
        'resume.no_credits':   "У вас закончились кредиты на генерацию резюме.\n\nПополни баланс:",
        'resume.ready':        "📄 <b>Ваше резюме готово!</b>",
        'resume.pdf_caption':  "📄 Ваше резюме в формате PDF",
        'resume.pdf_error':    "⚠️ PDF не удалось создать: {error}",
        'resume.wrong_type':   "📋 Пожалуйста, отправь текст вакансии.",
        'resume.wrong_exp':    "💼 Пожалуйста, опиши опыт работы текстом.",
        'resume.wrong_edu':    "🎓 Пожалуйста, напиши об образовании текстом.",
        'resume.wrong_skills': "🛠 Пожалуйста, напиши навыки текстом.",

        # Cover letter
        'cover.ask_vacancy':   "📋 Отправьте <b>текст вакансии</b> для сопроводительного письма:",
        'cover.generating':    "⏳ Пишу сопроводительное письмо...",
        'cover.no_credits':    "У вас закончились кредиты на сопроводительные письма.\n\nПополни баланс:",
        'cover.ready':         "✉️ <b>Сопроводительное письмо готово!</b>",
        'cover.wrong_type':    "📋 Пожалуйста, напиши текст вакансии.",

        # Interview
        'interview.ask_vacancy':  "📋 Отправьте <b>текст вакансии</b>, на которую готовитесь:",
        'interview.starting':     "⏳ Начинаю собеседование...",
        'interview.no_credits':   "Симуляция собеседования — платная функция.\n\nПополни баланс:",
        'interview.finish_prompt':"⏳ Подвожу итоги собеседования...",
        'interview.btn_finish':   "⏭ Завершить собеседование",
        'interview.btn_exit':     "🏠 Выйти из собеседования",

        # Vacancy analysis
        'vacancy.ask':       "📋 Вставьте <b>текст вакансии</b> для анализа:",
        'vacancy.analyzing': "🔍 Анализирую вакансию...",
        'vacancy.result':    "🔍 <b>Анализ вакансии:</b>",
        'vacancy.wrong_type':"📋 Пожалуйста, напиши текст вакансии.",

        # Payment
        'pay.basic':        "📄 Базовый — 299₽",
        'pay.pro':          "⭐ Про — 790₽",
        'pay.vip':          "👑 VIP 30 дней — 1990₽",
        'pay.ai50':         "💬 50 сообщений AI — 149₽",
        'pay.ai200':        "💬 200 сообщений AI — 399₽",
        'pay.ai_unlimited': "💬 AI Безлимит 30 дней — 690₽",
        'pay.method_crypto':"💎 Криптовалюта (USDT)",
        'pay.method_rucard':"🇷🇺 Карта РФ (перевод)",
        'pay.method_revolut':"💳 Revolut",
        'pay.check':        "✅ Проверить оплату",
        'pay.i_paid':       "✅ Я оплатил — отправить чек",

        # AI assistant
        'assistant.no_credits': "У тебя закончились сообщения AI-ассистента.\n\nПополни баланс:",

        # Generic
        'no_credits': "У вас недостаточно кредитов.\n\nПополни баланс:",
        'error.generic': "⚠️ Произошла ошибка. Попробуйте ещё раз или обратитесь в поддержку.",
        'error.server_down': (
            "⚙️ <b>Временный сбой</b>\n\n"
            "Что-то пошло не так на нашем сервере. "
            "Мы уже в курсе и чиним!\n\n"
            "Попробуйте через несколько минут 🙏"
        ),
        'error.maintenance': (
            "⚙️ <b>Технические работы</b>\n\n"
            "На сервере временный сбой — мы уже чиним.\n"
            "Все ваши данные в безопасности.\n\n"
            "Бот вернётся в работу совсем скоро! 🙏"
        ),

        # Profile
        'profile.header': (
            "👤 <b>Твой профиль:</b>\n"
            "Имя: {full_name}\n"
            "Подписка: {subscription_type}\n\n"
            "💰 <b>Баланс:</b>\n"
            "📄 Резюме: {credits_resume}\n"
            "✉️ Письма: {credits_cover_letter}\n"
            "🎯 Собесы: {credits_interview}\n"
            "💬 AI-сообщения: {credits_assistant}\n\n"
            "📊 <b>Статистика:</b>\n"
            "Резюме создано: {total_resumes_generated}\n"
            "AI-сообщений отправлено: {total_assistant_messages}\n"
            "Потрачено: {total_spent_rub}₽"
        ),
        'profile.sub.free':               "Бесплатный",
        'profile.sub.basic':              "Базовый",
        'profile.sub.pro':                "Про",
        'profile.sub.vip':                "VIP",
        'profile.sub.assistant_unlimited':"AI Безлимит",

        # Referral
        'referral.header': (
            "🎁 <b>Реферальная программа</b>\n\n"
            "Пригласи друга и получи <b>3 бесплатных сообщения AI-ассистента!</b>\n\n"
            "Твоя ссылка:\n"
            "<code>https://t.me/{bot_username}?start=ref_{referral_code}</code>\n\n"
            "Приглашено друзей: {referral_count}"
        ),

        # Support
        'support.text': (
            "🆘 По всем вопросам пишите нам напрямую.\n"
            "Обычно отвечаем в течение 1 часа."
        ),

        # Maintenance / admin
        'admin.report_generating': "📊 Генерирую отчёт…",
        'admin.maintenance_on':    "📢 Sending maintenance notification to all users…",
        'admin.maintenance_off':   "✅ Sending recovery notification to all users…",
        'admin.report_error':      "❌ Ошибка отчёта: {error}",

        # Interview (extra)
        'interview.started':       "🎯 <b>Собеседование началось!</b>",
        'interview.finish_header': "📊 <b>Итоги собеседования:</b>",
        'interview.finish_error':  "⚠️ Не удалось подвести итоги: {error}\n\nПопробуй начать собеседование заново.",
        'interview.wrong_vacancy': "📋 Пожалуйста, напиши текст вакансии.",
        'interview.wrong_answer':  "💬 Пожалуйста, напиши свой ответ текстом.",

        # AI Assistant
        'assistant.intro':         (
            "💬 <b>AI-ассистент активирован!</b>\n\n"
            "Задай мне любой вопрос — я помогу с карьерой, текстами,\n"
            "обучением и чем угодно ещё.\n\n"
            "💰 Осталось сообщений: <b>{credits_assistant}</b>\n\n"
            "Для выхода нажми кнопку ниже."
        ),
        'assistant.low_credits':   "\n\n⚠️ <i>Осталось {n} сообщений.</i>",
        'assistant.last_message':  "\n\n❌ <i>Это было последнее сообщение.</i>",
        'assistant.wrong_type':    "💬 Пожалуйста, напиши свой вопрос текстом.",
        'assistant.history_cleared':"История очищена ✅",

        # Payment — user-facing
        'pay.loading':             "⏳ Создаю инвойс...",
        'pay.crypto_unavailable':  "Криптооплата временно недоступна.",
        'pay.success':             "✅ Оплата подтверждена! Пакет «{name}» активирован.\nВаш баланс обновлён.",
        'pay.check_pending':       (
            "⏳ <b>Платёж ещё не подтверждён.</b>\n\n"
            "Оплати через @CryptoBot и нажми кнопку ещё раз.\n"
            "Обычно занимает 1-2 минуты."
        ),
        'pay.not_found':           "Платёж не найден. Если оплата прошла — обратись в поддержку.",
        'pay.checking':            "⏳ Проверяю...",
        'pay.receipt_ask':         "📸 Отправь скриншот подтверждения оплаты (фото):",
        'pay.receipt_sent':        (
            "✅ Чек получен! Мы проверим оплату и зачислим кредиты в течение нескольких минут.\n\n"
            "Ожидай уведомления."
        ),
        'pay.receipt_checking':    "🔍 Проверяю чек с помощью AI... Займёт несколько секунд.",
        'pay.receipt_wrong_type':  "📸 Пожалуйста, отправь скриншот оплаты как <b>фото</b>.",
        'pay.auto_approved':       "✅ <b>Оплата подтверждена автоматически!</b>\n\nПакет «{name}» активирован. Баланс обновлён. 🎉",
        'pay.approved_user':       "✅ Оплата подтверждена! Пакет «{name}» активирован. Баланс обновлён.",
        'pay.rejected_user':       (
            "❌ Оплата не подтверждена.\n\n"
            "Если ты действительно оплатил — напиши в поддержку и приложи скриншот."
        ),
        'pay.error_grant':         "⚠️ Ошибка начисления: {error}",
        'pay.crypto_pending':      (
            "💎 <b>Оплата криптовалютой (USDT)</b>\n\n"
            "Сумма: <b>{usdt} USDT</b>\n\n"
            "👉 Перейди по ссылке и оплати через @CryptoBot:\n"
            "{pay_url}\n\n"
            "После оплаты нажми кнопку ниже."
        ),
        'pay.manual_ru':           (
            "🇷🇺 <b>Перевод на карту РФ</b>\n\n"
            "Сумма: <b>{amount}₽</b>\n"
            "Банк: <b>{bank}</b>\n"
            "Карта: <code>{card}</code>\n"
            "Получатель: <b>{holder}</b>\n\n"
            "После оплаты нажми кнопку ниже и отправь скриншот."
        ),
        'pay.manual_revolut':      (
            "💳 <b>Перевод на Revolut</b>\n\n"
            "Сумма: <b>{amount_rub}₽</b> (≈ <b>{amount_usdt} USDT</b>)\n"
            "Revolut: <b>{revolut}</b>\n\n"
            "Скопируй тег и сделай перевод в Revolut, затем нажми кнопку ниже."
        ),

        # Support
        'support.ask':             (
            "🆘 <b>Поддержка РезюмеАИ</b>\n\n"
            "Опиши свою проблему или задай вопрос — сообщение сразу попадёт к нам.\n\n"
            "Обычно отвечаем в течение 1 часа."
        ),
        'support.sent':            (
            "✅ Сообщение отправлено в поддержку!\n\n"
            "Мы ответим тебе здесь в ближайшее время."
        ),
        'support.wrong_type':      "📝 Пожалуйста, напиши своё сообщение текстом.",

        # Buy menu header
        'buy.header':              (
            "💰 <b>Пополнить баланс</b>\n\n"
            "Выбери пакет:"
        ),
    },
    # ────────────────────────────────────────────────────────────────────────
    'en': {
        # Start / Welcome
        'start.welcome': (
            "👋 <b>Hi! I'm ResumeAI</b>\n\n"
            "Your personal AI career consultant. 100% chance of landing a job.\n\n"
            "<b>What I can do:</b>\n"
            "📄 <b>Resume</b> — tailored to each job in 30 sec, no clichés\n"
            "✉️ <b>Cover Letter</b> — engaging and personalized\n"
            "🎯 <b>Interview Prep</b> — STAR method evaluation, finds weak spots\n"
            "🔍 <b>Job Analysis</b> — salary range, red flags, ATS keywords\n"
            "💬 <b>AI Assistant</b> — any career question, 24/7\n\n"
            "<b>Bonuses:</b>\n"
            "🧠 Remembers your profile — second resume in 1 click\n"
            "📬 Weekly career digest every Monday\n"
            "🎁 Invite friends — earn free resumes\n\n"
            "<b>Available for free right now:</b>\n"
            "• 1 resume  •  1 cover letter  •  3 AI messages\n\n"
            "👇 <b>Choose where to start:</b>"
        ),
        'start.choose_lang': "👋 Hi! Choose your language / Выбери язык:",
        'start.lang_set': "✅ Language set: <b>English</b>\n\nWelcome! 👇",

        # Language
        'lang.choose': "🌐 Choose your language / Выбери язык:",
        'lang.set_ru': "✅ Язык: <b>Русский</b>",
        'lang.set_en': "✅ Language: <b>English</b>",

        # Menu buttons
        'menu.resume':      "📄 Build Resume",
        'menu.cover_letter':"✉️ Cover Letter",
        'menu.interview':   "🎯 Mock Interview",
        'menu.vacancy':     "🔍 Analyze Job",
        'menu.assistant':   "💬 AI Assistant",
        'menu.profile':     "👤 My Profile",
        'menu.buy':         "💳 Buy Credits",
        'menu.referral':    "🎁 Invite a Friend",
        'menu.support':     "🆘 Support",
        'menu.webapp':      "🌐 Open Mini App",

        # Common buttons
        'btn.menu':            "🏠 Main Menu",
        'btn.cancel':          "❌ Cancel",
        'btn.back':            "◀️ Back",
        'btn.resume_for_job':  "📄 Create resume for this job",
        'btn.cover_for_job':   "✉️ Cover letter for this job",
        'btn.interview_for_job':"🎯 Mock interview for this job",
        'btn.new_resume':      "📄 New Resume",
        'btn.repeat':          "🔄 Try Again",
        'btn.ai_question':     "💬 Ask AI",
        'btn.clear_history':   "🗑 Clear History",
        'btn.share':           "🎁 Share → get a free resume",
        'btn.top_up':          "💳 Top Up Balance",

        # Resume flow
        'resume.ask_vacancy':  "📋 Paste the <b>job description</b> (copy it from LinkedIn, Indeed, or another site):",
        'resume.ask_experience':"💼 Tell me about your <b>work experience</b> (briefly — key roles and achievements):",
        'resume.ask_education':"🎓 <b>Education</b> (university, field of study, graduation year):",
        'resume.ask_skills':   "🛠 <b>Key skills</b> (comma-separated):",
        'resume.generating':   "⏳ Creating your perfect resume for this job...",
        'resume.no_credits':   "You've run out of resume credits.\n\nTop up your balance:",
        'resume.ready':        "📄 <b>Your resume is ready!</b>",
        'resume.pdf_caption':  "📄 Your resume as a PDF",
        'resume.pdf_error':    "⚠️ Could not generate PDF: {error}",
        'resume.wrong_type':   "📋 Please send the job description as text.",
        'resume.wrong_exp':    "💼 Please describe your work experience as text.",
        'resume.wrong_edu':    "🎓 Please describe your education as text.",
        'resume.wrong_skills': "🛠 Please list your skills as text.",

        # Cover letter
        'cover.ask_vacancy':   "📋 Paste the <b>job description</b> for the cover letter:",
        'cover.generating':    "⏳ Writing your cover letter...",
        'cover.no_credits':    "You've run out of cover letter credits.\n\nTop up your balance:",
        'cover.ready':         "✉️ <b>Your cover letter is ready!</b>",
        'cover.wrong_type':    "📋 Please send the job description as text.",

        # Interview
        'interview.ask_vacancy':  "📋 Paste the <b>job description</b> you're preparing for:",
        'interview.starting':     "⏳ Starting your mock interview...",
        'interview.no_credits':   "Mock interview is a paid feature.\n\nTop up your balance:",
        'interview.finish_prompt':"⏳ Summarizing your interview results...",
        'interview.btn_finish':   "⏭ Finish Interview",
        'interview.btn_exit':     "🏠 Exit Interview",

        # Vacancy analysis
        'vacancy.ask':       "📋 Paste the <b>job description</b> to analyze:",
        'vacancy.analyzing': "🔍 Analyzing the job posting...",
        'vacancy.result':    "🔍 <b>Job Analysis:</b>",
        'vacancy.wrong_type':"📋 Please send the job description as text.",

        # Payment
        'pay.basic':        "📄 Basic — 299₽",
        'pay.pro':          "⭐ Pro — 790₽",
        'pay.vip':          "👑 VIP 30 days — 1990₽",
        'pay.ai50':         "💬 50 AI messages — 149₽",
        'pay.ai200':        "💬 200 AI messages — 399₽",
        'pay.ai_unlimited': "💬 Unlimited AI 30 days — 690₽",
        'pay.method_crypto':"💎 Crypto (USDT)",
        'pay.method_rucard':"🇷🇺 Russian card (transfer)",
        'pay.method_revolut':"💳 Revolut",
        'pay.check':        "✅ Check Payment",
        'pay.i_paid':       "✅ I've paid — send receipt",

        # AI assistant
        'assistant.no_credits': "You've used up your free AI messages.\n\nTop up your balance:",

        # Generic
        'no_credits': "You don't have enough credits.\n\nTop up your balance:",
        'error.generic': "⚠️ An error occurred. Please try again or contact support.",
        'error.server_down': (
            "⚙️ <b>Temporary issue</b>\n\n"
            "Something went wrong on our server. "
            "We're aware and fixing it!\n\n"
            "Try again in a few minutes 🙏"
        ),
        'error.maintenance': (
            "⚙️ <b>Maintenance</b>\n\n"
            "Server is temporarily unavailable — we're fixing it.\n"
            "All your data is safe.\n\n"
            "Bot will be back very soon! 🙏"
        ),

        # Profile
        'profile.header': (
            "👤 <b>Your Profile:</b>\n"
            "Name: {full_name}\n"
            "Plan: {subscription_type}\n\n"
            "💰 <b>Balance:</b>\n"
            "📄 Resumes: {credits_resume}\n"
            "✉️ Cover Letters: {credits_cover_letter}\n"
            "🎯 Interviews: {credits_interview}\n"
            "💬 AI Messages: {credits_assistant}\n\n"
            "📊 <b>Stats:</b>\n"
            "Resumes created: {total_resumes_generated}\n"
            "AI messages sent: {total_assistant_messages}\n"
            "Total spent: {total_spent_rub}₽"
        ),
        'profile.sub.free':               "Free",
        'profile.sub.basic':              "Basic",
        'profile.sub.pro':                "Pro",
        'profile.sub.vip':                "VIP",
        'profile.sub.assistant_unlimited':"AI Unlimited",

        # Referral
        'referral.header': (
            "🎁 <b>Referral Program</b>\n\n"
            "Invite a friend and get <b>3 free AI assistant messages!</b>\n\n"
            "Your link:\n"
            "<code>https://t.me/{bot_username}?start=ref_{referral_code}</code>\n\n"
            "Friends invited: {referral_count}"
        ),

        # Support
        'support.text': (
            "🆘 For all questions, contact us directly.\n"
            "We usually reply within 1 hour."
        ),

        # Maintenance / admin (admin-only, English is fine)
        'admin.report_generating': "📊 Generating report…",
        'admin.maintenance_on':    "📢 Sending maintenance notification to all users…",
        'admin.maintenance_off':   "✅ Sending recovery notification to all users…",
        'admin.report_error':      "❌ Report error: {error}",

        # Interview (extra)
        'interview.started':       "🎯 <b>Interview started!</b>",
        'interview.finish_header': "📊 <b>Interview Results:</b>",
        'interview.finish_error':  "⚠️ Could not generate results: {error}\n\nTry starting the interview again.",
        'interview.wrong_vacancy': "📋 Please send the job description as text.",
        'interview.wrong_answer':  "💬 Please type your answer as text.",

        # AI Assistant
        'assistant.intro':         (
            "💬 <b>AI Assistant activated!</b>\n\n"
            "Ask me anything — career advice, writing help,\n"
            "learning tips, and more.\n\n"
            "💰 Messages remaining: <b>{credits_assistant}</b>\n\n"
            "Press the button below to exit."
        ),
        'assistant.low_credits':   "\n\n⚠️ <i>{n} messages remaining.</i>",
        'assistant.last_message':  "\n\n❌ <i>That was your last message.</i>",
        'assistant.wrong_type':    "💬 Please type your question as text.",
        'assistant.history_cleared':"History cleared ✅",

        # Payment — user-facing
        'pay.loading':             "⏳ Creating invoice...",
        'pay.crypto_unavailable':  "Crypto payment is temporarily unavailable.",
        'pay.success':             "✅ Payment confirmed! Package «{name}» activated.\nYour balance has been updated.",
        'pay.check_pending':       (
            "⏳ <b>Payment not confirmed yet.</b>\n\n"
            "Complete payment via @CryptoBot and press the button again.\n"
            "Usually takes 1-2 minutes."
        ),
        'pay.not_found':           "Payment not found. If you've already paid — contact support.",
        'pay.checking':            "⏳ Checking...",
        'pay.receipt_ask':         "📸 Send a screenshot of your payment confirmation (photo):",
        'pay.receipt_sent':        (
            "✅ Receipt received! We'll verify your payment and add credits within a few minutes.\n\n"
            "Watch for a notification here."
        ),
        'pay.receipt_checking':    "🔍 Verifying receipt with AI... This takes a few seconds.",
        'pay.receipt_wrong_type':  "📸 Please send the payment screenshot as a <b>photo</b>.",
        'pay.auto_approved':       "✅ <b>Payment confirmed automatically!</b>\n\nPackage «{name}» activated. Balance updated. 🎉",
        'pay.approved_user':       "✅ Payment confirmed! Package «{name}» activated. Balance updated.",
        'pay.rejected_user':       (
            "❌ Payment not confirmed.\n\n"
            "If you did pay — contact support and include a screenshot."
        ),
        'pay.error_grant':         "⚠️ Error granting credits: {error}",
        'pay.crypto_pending':      (
            "💎 <b>Crypto payment (USDT)</b>\n\n"
            "Amount: <b>{usdt} USDT</b>\n\n"
            "👉 Follow the link and pay via @CryptoBot:\n"
            "{pay_url}\n\n"
            "Press the button below after payment."
        ),
        'pay.manual_ru':           (
            "🇷🇺 <b>Transfer to Russian card</b>\n\n"
            "Amount: <b>{amount}₽</b>\n"
            "Bank: <b>{bank}</b>\n"
            "Card: <code>{card}</code>\n"
            "Recipient: <b>{holder}</b>\n\n"
            "After payment press the button below and send a screenshot."
        ),
        'pay.manual_revolut':      (
            "💳 <b>Revolut transfer</b>\n\n"
            "Amount: <b>{amount_rub}₽</b> (≈ <b>{amount_usdt} USDT</b>)\n"
            "Revolut tag: <b>{revolut}</b>\n\n"
            "Copy the tag, make the transfer in Revolut, then press the button below."
        ),

        # Support
        'support.ask':             (
            "🆘 <b>ResumeAI Support</b>\n\n"
            "Describe your issue or ask a question — your message goes straight to our team.\n\n"
            "We usually reply within 1 hour."
        ),
        'support.sent':            (
            "✅ Your message has been sent to support!\n\n"
            "We'll reply to you here shortly."
        ),
        'support.wrong_type':      "📝 Please type your message as text.",

        # Buy menu header
        'buy.header':              (
            "💰 <b>Top Up Balance</b>\n\n"
            "Choose a package:"
        ),
    },
}


def t(lang: str | None, key: str, **kwargs: object) -> str:
    """
    Return the translated string for *key* in *lang*.

    Falls back to Russian when the key or language is missing.
    Supports keyword-argument substitution via str.format(**kwargs).

    Example:
        t('en', 'resume.pdf_error', error="timeout")
    """
    lang = lang if lang in STRINGS else 'ru'
    text: str = STRINGS[lang].get(key) or STRINGS['ru'].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text
