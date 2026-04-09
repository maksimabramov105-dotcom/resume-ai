#!/usr/bin/env python3
"""
content_generator.py — AI content generation for all marketing channels.

Uses OpenRouter (OpenAI-compatible) → Claude claude-3-5-haiku model.
Generates 5 formats per topic: Reddit, Twitter thread, Telegra.ph, VK, Quora.
Saves to content_output/YYYY-MM-DD_topic-slug/

Usage:
    python3 content_generator.py                  # generate one random topic
    python3 content_generator.py --all            # generate all 30 topics
    python3 content_generator.py --topic "Ошибки в резюме"
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

# Add project root to path so we can import shared config
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI  # OpenRouter uses the OpenAI-compatible SDK

from content_marketing.config import (
    OPENROUTER_API_KEY,
    CLAUDE_MODEL,
    BOT_LINK,
    BOT_NAME,
    BOT_USERNAME,
    CONTENT_DIR,
    LOGS_DIR,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "content_generation_log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── 30 Topics ────────────────────────────────────────────────────────────────
TOPICS = [
    "Как написать резюме без опыта работы",
    "Ошибки в резюме которые отпугивают HR",
    "Как пройти ATS фильтр резюме",
    "Подготовка к собеседованию метод STAR",
    "Зарплатные переговоры — как не продешевить",
    "Как сменить профессию в 30 лет",
    "Красные флаги в вакансиях которые надо игнорировать",
    "Сопроводительное письмо которое читают",
    "Как найти работу через Telegram",
    "HR секреты: что они реально ищут в резюме",
    "Как описать достижения в резюме с цифрами",
    "Почему тебя не зовут на собеседование",
    "LinkedIn профиль для поиска работы в 2025",
    "Как написать резюме за рубеж на английском",
    "Навыки которые работодатели ищут в 2025 году",
    "Как подготовиться к техническому интервью",
    "Резюме для смены карьеры: что убрать что добавить",
    "Как использовать AI для поиска работы",
    "Самопрезентация на собеседовании 60 секунд",
    "Работа на фрилансе: как найти первого клиента",
    "Как ответить на вопрос о слабых сторонах",
    "Портфолио вместо резюме: когда и как",
    "Нетворкинг для интровертов: как искать работу без связей",
    "Удалённая работа: как найти и не облажаться",
    "Что писать в разделе 'О себе' в резюме",
    "Как выйти из декрета обратно на рынок труда",
    "Gap year в резюме: как объяснить пробел",
    "Как писать резюме если работал в стартапе",
    "Переезд за границу: поиск работы с нуля",
    "Автоматизация поиска работы: инструменты 2025",
]


def slugify(text: str) -> str:
    """Convert topic to filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text.strip())
    return text[:60]


def get_output_dir(topic: str) -> Path:
    """Return (and create) the output directory for a topic."""
    slug = slugify(topic)
    folder = CONTENT_DIR / f"{date.today().isoformat()}_{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def call_claude(system_prompt: str, user_prompt: str, max_tokens: int = 1200) -> str:
    """
    Call Claude claude-3-5-haiku via OpenRouter (OpenAI-compatible endpoint).
    Retries once on rate-limit (429). Returns the response text.
    """
    client = OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=CLAUDE_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.85,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err and attempt == 0:
                log.warning("Rate limited — waiting 60s before retry…")
                time.sleep(60)
                continue
            raise


# ── Format generators ─────────────────────────────────────────────────────────

def generate_reddit(topic: str) -> str:
    system = (
        "You are a real person sharing genuine career advice on Reddit. "
        "Write in first person, casual tone. Sound like a human, not a marketer. "
        "NEVER use phrases like 'I discovered', 'game changer', or 'revolutionize'. "
        "The post should feel like a real personal experience."
    )
    user = f"""Write a Reddit post about: "{topic}"

Rules:
- Title: genuine question or statement, max 100 chars, no clickbait buzzwords
- Body: 200-300 words, personal story format (I was struggling with X, then Y happened…)
- Mention {BOT_NAME} bot (@{BOT_USERNAME}) naturally in the last paragraph as a tool that helped, with link: {BOT_LINK}
- Tone: helpful, honest, slightly self-deprecating
- Target: r/resumes or r/cscareeradvice audience
- Language: English

Output format:
TITLE: [title here]

BODY:
[body here]"""
    return call_claude(system, user, max_tokens=600)


def generate_twitter_thread(topic: str) -> str:
    system = (
        "You are a career coach with 50k Twitter followers. "
        "Write punchy, value-packed threads. No fluff. "
        "Each tweet must be self-contained and shareable."
    )
    user = f"""Write a 7-tweet Twitter/X thread about: "{topic}"

Rules:
- Tweet 1: Hook — bold stat, controversial take, or shocking fact. Start with 🧵
- Tweets 2-6: One actionable insight each. Use numbers. Short sentences.
- Tweet 7: CTA — mention @{BOT_USERNAME} and link: {BOT_LINK}
- Each tweet: under 270 characters (leave buffer for RT)
- Language: English
- Add relevant emoji to each tweet (max 2 per tweet)

Output format:
Tweet 1/7:
[text]

Tweet 2/7:
[text]

...and so on"""
    return call_claude(system, user, max_tokens=700)


def generate_telegraph_article(topic: str) -> str:
    system = (
        "Ты опытный карьерный консультант и автор блога. "
        "Пишешь практичные статьи для русскоязычной аудитории. "
        "Стиль: экспертный но доступный, без воды, с конкретными советами."
    )
    user = f"""Напиши статью для Telegra.ph на тему: "{topic}"

Требования:
- Длина: 600-800 слов
- Структура:
  * SEO-заголовок с ключевым словом (отдельная строка начинающаяся с "TITLE: ")
  * Вступление 2-3 предложения которое сразу цепляет
  * 4-5 разделов с подзаголовками (## Подзаголовок)
  * Практические советы, конкретные примеры, цифры
  * Последний раздел: "Автоматизация с AI" — упомяни {BOT_NAME} бот и ссылку {BOT_LINK}
- Язык: русский
- Тон: экспертный, помогающий, без воды

Формат вывода:
TITLE: [заголовок]

[текст статьи]"""
    return call_claude(system, user, max_tokens=1200)


def generate_vk_post(topic: str) -> str:
    system = (
        "Ты SMM-менеджер Telegram бота для поиска работы. "
        "Пишешь посты для ВКонтакте — живым языком, с эмодзи, но по делу. "
        "Аудитория: соискатели 20-40 лет в России и СНГ."
    )
    user = f"""Напиши пост для ВКонтакте на тему: "{topic}"

Требования:
- Длина: 150-200 слов
- Начни с цепляющего первого предложения (читают только первые 2 строки)
- 3-4 практических совета или факта
- Упомяни {BOT_NAME} и ссылку {BOT_LINK} естественно
- Эмодзи уместно, не перебарщивай (3-5 штук)
- Хэштеги в конце: #резюме #карьера #работа #AI #поискработы #телеграм
- Язык: русский
- Тон: дружелюбный, полезный

Выведи только текст поста, готовый к публикации."""
    return call_claude(system, user, max_tokens=400)


def generate_quora_answer(topic: str) -> str:
    system = (
        "You are a senior HR professional and career coach answering on Quora. "
        "Write authoritative, practical answers. "
        "Sound like a real expert, not a salesperson."
    )
    user = f"""Write a Quora-style answer related to: "{topic}"

Rules:
- First, write the question this answers (start with "Q: ")
- Answer: 150-200 words
- Authoritative but approachable tone
- Include 2-3 specific, actionable tips
- Mention {BOT_NAME} bot as "a tool I've been recommending to clients" with link: {BOT_LINK}
- Language: English

Output format:
Q: [question]

A:
[answer]"""
    return call_claude(system, user, max_tokens=400)


# ── Main generator ─────────────────────────────────────────────────────────

def generate_for_topic(topic: str) -> dict:
    """
    Generate all 5 formats for one topic.
    Returns dict with paths to saved files.
    """
    log.info("Generating content for: %s", topic)
    out_dir = get_output_dir(topic)
    saved = {}

    formats = [
        ("reddit.txt",            generate_reddit),
        ("twitter_thread.txt",    generate_twitter_thread),
        ("telegraph_article.txt", generate_telegraph_article),
        ("vk_post.txt",           generate_vk_post),
        ("quora_answer.txt",      generate_quora_answer),
    ]

    for filename, generator in formats:
        filepath = out_dir / filename
        # Skip if already generated (idempotent)
        if filepath.exists():
            log.info("  ↷ %s already exists, skipping", filename)
            saved[filename] = str(filepath)
            continue

        try:
            log.info("  → Generating %s…", filename)
            content = generator(topic)
            filepath.write_text(content, encoding="utf-8")
            saved[filename] = str(filepath)
            log.info("  ✓ Saved %s (%d chars)", filename, len(content))
            # Polite delay between API calls to avoid rate limits
            time.sleep(3)
        except Exception as e:
            log.error("  ✗ Failed %s: %s", filename, e)
            saved[filename] = None

    # Save metadata
    meta = {
        "topic": topic,
        "date": date.today().isoformat(),
        "files": saved,
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    log.info("Done: %s → %s", topic, out_dir)
    return saved


def main():
    parser = argparse.ArgumentParser(description="Generate marketing content")
    parser.add_argument("--all",   action="store_true", help="Generate all 30 topics")
    parser.add_argument("--topic", type=str,            help="Generate specific topic")
    parser.add_argument("--list",  action="store_true", help="List all topics")
    args = parser.parse_args()

    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY not set in environment")
        sys.exit(1)

    if args.list:
        for i, t in enumerate(TOPICS, 1):
            print(f"{i:2}. {t}")
        return

    if args.topic:
        topics_to_generate = [args.topic]
    elif args.all:
        topics_to_generate = TOPICS
    else:
        # Default: pick next ungenerated topic (for weekly scheduler)
        generated_slugs = {d.name.split("_", 1)[1] if "_" in d.name else ""
                           for d in CONTENT_DIR.iterdir() if d.is_dir()}
        topics_to_generate = []
        for t in TOPICS:
            if slugify(t) not in generated_slugs:
                topics_to_generate = [t]
                break
        if not topics_to_generate:
            log.info("All topics already generated. Re-generating first topic.")
            topics_to_generate = [TOPICS[0]]

    log.info("Generating %d topic(s)…", len(topics_to_generate))
    for topic in topics_to_generate:
        try:
            generate_for_topic(topic)
        except Exception as e:
            log.error("Failed topic '%s': %s", topic, e)
        if len(topics_to_generate) > 1:
            # Delay between topics when generating all
            time.sleep(10)

    log.info("Content generation complete.")


if __name__ == "__main__":
    main()
