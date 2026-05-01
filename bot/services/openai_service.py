import asyncio
import os

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _chat_completion_with_retry(model, messages, max_tokens, temperature):
    return await asyncio.wait_for(
        client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        ),
        timeout=45.0,
    )


async def chat_completion(
    messages: list,
    model: str = "gpt-4o-mini",
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> tuple[str, int]:
    """Universal method for all bot features. Returns (response text, tokens used)."""
    try:
        response = await _chat_completion_with_retry(model, messages, max_tokens, temperature)
        text = response.choices[0].message.content
        tokens = response.usage.total_tokens
        return text, tokens
    except asyncio.TimeoutError:
        return "⚠️ AI did not respond in time. Please try again.", 0
    except Exception as e:
        return f"⚠️ AI error: {str(e)}", 0


_EN_LANG_PREFIX = "IMPORTANT: Respond entirely in English. Do not use any Russian text.\n\n"


def _sys(prompt: str, lang: str) -> str:
    return (_EN_LANG_PREFIX + prompt) if lang == 'en' else prompt


async def generate_resume(
    vacancy: str, experience: str, education: str, skills: str, lang: str = 'ru'
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
            {"role": "system", "content": _sys(RESUME_SYSTEM_PROMPT, lang)},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2000,
        temperature=0.6,
    )


async def generate_cover_letter(vacancy: str, candidate_summary: str, lang: str = 'ru') -> tuple[str, int]:
    from prompts.cover_letter_prompt import COVER_LETTER_SYSTEM_PROMPT, COVER_LETTER_USER_PROMPT

    return await chat_completion(
        messages=[
            {"role": "system", "content": _sys(COVER_LETTER_SYSTEM_PROMPT, lang)},
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


async def start_interview(vacancy: str, candidate_summary: str, lang: str = 'ru') -> tuple[str, int]:
    from prompts.interview_prompt import INTERVIEW_SYSTEM_PROMPT, INTERVIEW_START_PROMPT

    return await chat_completion(
        messages=[
            {"role": "system", "content": _sys(INTERVIEW_SYSTEM_PROMPT, lang)},
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
    vacancy: str, candidate_summary: str, history: list[dict], user_answer: str, lang: str = 'ru'
) -> tuple[str, int]:
    from prompts.interview_prompt import INTERVIEW_SYSTEM_PROMPT, INTERVIEW_START_PROMPT

    messages = [
        {"role": "system", "content": _sys(INTERVIEW_SYSTEM_PROMPT, lang)},
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
    vacancy: str, candidate_summary: str, history: list[dict], lang: str = 'ru'
) -> tuple[str, int]:
    from prompts.interview_prompt import INTERVIEW_SYSTEM_PROMPT, INTERVIEW_START_PROMPT

    messages = [
        {"role": "system", "content": _sys(INTERVIEW_SYSTEM_PROMPT, lang)},
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
        "content": "Please end the interview and give a final evaluation: score 1-10, strengths, weaknesses, and specific recommendations.",
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
