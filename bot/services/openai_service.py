import asyncio

from openai import AsyncOpenAI
import os

# Поддержка OpenRouter и обычного OpenAI
# Если OPENROUTER_API_KEY задан — используем OpenRouter
_openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
_openai_key = os.getenv("OPENAI_API_KEY", "")

if _openrouter_key:
    client = AsyncOpenAI(
        api_key=_openrouter_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://t.me/topbestworkerbot",
            "X-Title": "ResumeAI Bot",
        },
    )
else:
    client = AsyncOpenAI(api_key=_openai_key)


async def chat_completion(
    messages: list,
    model: str = "gpt-4o-mini",
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> tuple[str, int]:
    """
    Universal method for all bot features.
    Returns (response text, tokens used).
    """
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            ),
            timeout=45.0,
        )
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return text, tokens
    except asyncio.TimeoutError:
        return "⚠️ AI не ответил вовремя. Попробуйте ещё раз.", 0
    except Exception as e:
        return f"Произошла ошибка при обращении к AI: {str(e)}", 0


async def generate_resume(
    vacancy: str, experience: str, education: str, skills: str
) -> tuple[str, int]:
    from prompts.resume_prompt import RESUME_SYSTEM_PROMPT, RESUME_USER_PROMPT_TEMPLATE

    user_prompt = RESUME_USER_PROMPT_TEMPLATE.format(
        vacancy_text=vacancy,
        experience=experience,
        education=education,
        skills=skills,
        additional_info="",
    )
    return await chat_completion(
        messages=[
            {"role": "system", "content": RESUME_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2000,
        temperature=0.6,
    )


async def generate_cover_letter(vacancy: str, candidate_summary: str) -> tuple[str, int]:
    from prompts.cover_letter_prompt import COVER_LETTER_SYSTEM_PROMPT, COVER_LETTER_USER_PROMPT

    return await chat_completion(
        messages=[
            {"role": "system", "content": COVER_LETTER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": COVER_LETTER_USER_PROMPT.format(
                    vacancy_text=vacancy, candidate_summary=candidate_summary
                ),
            },
        ],
        max_tokens=1000,
        temperature=0.7,
    )


async def start_interview(vacancy: str, candidate_summary: str) -> tuple[str, int]:
    from prompts.interview_prompt import INTERVIEW_SYSTEM_PROMPT, INTERVIEW_START_PROMPT

    return await chat_completion(
        messages=[
            {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": INTERVIEW_START_PROMPT.format(
                    vacancy_text=vacancy, candidate_summary=candidate_summary
                ),
            },
        ],
        max_tokens=500,
        temperature=0.8,
    )


async def continue_interview(
    vacancy: str, candidate_summary: str, history: list[dict], user_answer: str
) -> tuple[str, int]:
    from prompts.interview_prompt import INTERVIEW_SYSTEM_PROMPT, INTERVIEW_START_PROMPT

    messages = [
        {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": INTERVIEW_START_PROMPT.format(
                vacancy_text=vacancy, candidate_summary=candidate_summary
            ),
        },
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_answer})
    return await chat_completion(messages=messages, max_tokens=600, temperature=0.8)


async def finish_interview(
    vacancy: str, candidate_summary: str, history: list[dict]
) -> tuple[str, int]:
    from prompts.interview_prompt import INTERVIEW_SYSTEM_PROMPT, INTERVIEW_START_PROMPT

    messages = [
        {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": INTERVIEW_START_PROMPT.format(
                vacancy_text=vacancy, candidate_summary=candidate_summary
            ),
        },
    ]
    messages.extend(history)
    messages.append({
        "role": "user",
        "content": "Пожалуйста, завершите собеседование и дайте финальную оценку кандидату: оценка 1-10, сильные стороны, слабые стороны и конкретные рекомендации.",
    })
    return await chat_completion(messages=messages, max_tokens=1000, temperature=0.7)


async def analyze_vacancy(vacancy: str) -> tuple[str, int]:
    from prompts.vacancy_analysis_prompt import VACANCY_ANALYSIS_PROMPT

    return await chat_completion(
        messages=[
            {"role": "user", "content": VACANCY_ANALYSIS_PROMPT.format(vacancy_text=vacancy)},
        ],
        max_tokens=1500,
        temperature=0.5,
    )
