# Habr.com — Техническая статья

**Заголовок:** Как я автоматизировал поиск работы с помощью Python, GPT-4 и hh.ru API

**Хабы:** Python, Карьера в IT, OpenAI, Автоматизация

---

После сокращения у меня было два варианта: методично рассылать резюме вручную, или один раз потратить неделю на автоматизацию и потом рассылать по 50 откликов в день без усилий. Я выбрал второй вариант.

Результат: 312 откликов за 7 дней, 12 приглашений на собеседование, 3 оффера.

## Архитектура системы

```
Telegram Bot (aiogram 3)
       |
       +-- FastAPI REST API (порт 8080)
       |       +-- /api/vacancies  — список найденных вакансий
       |       +-- /api/apply      — отправить отклик
       |       +-- /api/health     — мониторинг
       |
       +-- Background Worker
       |       +-- Парсинг hh.ru каждые 30 минут
       |       +-- Генерация резюме через OpenAI
       |       +-- Автоотклик через hh.ru API
       |
       +-- SQLite (aiosqlite)
               +-- users
               +-- vacancies
               +-- applications
               +-- resumes
```

Деплой на VPS с systemd: три сервиса (бот, API, воркер) + таймер health check каждые 5 минут.

## Ядро системы: тейлоринг резюме

Главная проблема массовой рассылки — одно и то же резюме работает плохо. ATS-системы крупных компаний фильтруют кандидатов по совпадению ключевых слов с требованиями вакансии.

Решение: для каждой вакансии генерировать отдельную версию резюме.

```python
async def generate_tailored_resume(base_resume, vacancy):
    prompt = f'''
Ты — опытный HR-консультант и карьерный коуч.
Задача: адаптировать резюме под конкретную вакансию.

Правила:
1. Не добавляй опыт, которого нет в исходном резюме
2. Переформулируй существующие пункты, используя язык вакансии
3. Выдели наиболее релевантный опыт на первый план
4. Используй ключевые слова из описания вакансии

Вакансия: {vacancy['title']} в {vacancy['company']}
Описание: {vacancy['description'][:500]}

Резюме для адаптации:
{base_resume}
'''
    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=1500,
    )
    return response.choices[0].message.content
```

Важный момент: используем `gpt-4o-mini` вместо `gpt-4`. Разница в качестве для этой задачи незначительная, разница в цене — в 15 раз.

## Интеграция с hh.ru API

hh.ru предоставляет полноценный REST API. Для отправки отклика нужен OAuth-токен пользователя:

```python
async def apply_to_vacancy(vacancy_id, resume_id, access_token, cover_letter=''):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.hh.ru/negotiations",
            headers={
                "Authorization": f"Bearer {access_token}",
                "HH-User-Agent": "ResumeAI/1.0 (support@resumeai.bot)",
            },
            json={
                "vacancy_id": vacancy_id,
                "resume_id": resume_id,
                "message": cover_letter,
            },
        ) as resp:
            if resp.status == 201:
                return {'success': True}
            return {'success': False, 'error': await resp.json()}
```

Лимиты hh.ru: не более 200 откликов в день с одного аккаунта. Мы ставим лимит 50/день по умолчанию — надёжнее и не привлекает внимания.

## Мониторинг

Health check запускается каждые 5 минут через systemd timer:

```python
async def main():
    checks = [check_bot_db, check_autoapply_api, check_hh_api, check_disk_space]
    results = await asyncio.gather(*[fn() for fn in checks])
    failures = [msg for ok, msg in results if not ok]
    if failures:
        await send_telegram_alert("\n".join(failures))
        # попытка авторестарта упавших сервисов
```

При падении сервиса — автоматический `systemctl restart`, ожидание 30 секунд, повторная проверка. Если не восстановился — алерт в Telegram.

## Стоимость эксплуатации

| Компонент | Стоимость |
|-----------|-----------|
| VPS (2 CPU, 4GB RAM) | ~500 руб/мес |
| OpenAI API (500 генераций/мес) | ~$10 |
| hh.ru API | бесплатно |
| SuperJob API | бесплатно |
| Домен | ~900 руб/год |

Итого: ~1400 руб/мес для полноценной работы.

## Попробовать

Бот доступен как @topbestworkerbot в Telegram. Бесплатный тариф: 3 автоотклика/день.
Веб-версия: resumeai.bot

Код написан на Python 3.11, aiogram 3, FastAPI. Если интересно — пишите вопросы в комментарии.
