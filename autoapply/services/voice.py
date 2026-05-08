"""
voice.py — Voice-to-resume pipeline.

Step 1: transcribe(audio_bytes, filename) -> str
    Calls OpenAI Whisper API to convert audio to text.

Step 2: structure_transcript(transcript) -> dict
    Calls GPT-4o-mini with resume_voice.txt prompt to extract
    structured resume JSON from the raw transcript.
"""
import json
import os
from pathlib import Path

import httpx

# Load the prompt at module import time
_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "resume_voice.txt"
_RESUME_VOICE_PROMPT: str = _PROMPT_PATH.read_text(encoding="utf-8")

# Required top-level keys for a valid resume blob
_REQUIRED_KEYS = {"name", "headline", "summary", "experience", "education", "skills", "languages", "contact"}


async def transcribe(audio_bytes: bytes, filename: str) -> str:
    """Transcribe audio bytes using OpenAI Whisper API.

    Args:
        audio_bytes: Raw audio file bytes.
        filename: Original filename (used to determine MIME type).

    Returns:
        Transcript text string.

    Raises:
        ValueError: If OPENAI_API_KEY is not set.
        httpx.HTTPStatusError: If the Whisper API returns an error.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY required for voice transcription")

    # Determine MIME type from filename extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
    mime_map = {
        "webm": "audio/webm",
        "mp3": "audio/mpeg",
        "mp4": "audio/mp4",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
        "wav": "audio/wav",
        "flac": "audio/flac",
    }
    mime_type = mime_map.get(ext, "audio/webm")

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={
                "file": (filename, audio_bytes, mime_type),
                "model": (None, "whisper-1"),
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("text", "")


async def structure_transcript(transcript: str) -> dict:
    """Structure a raw speech transcript into a resume JSON blob.

    Uses OpenRouter if OPENROUTER_API_KEY is set, otherwise falls back to
    direct OpenAI using OPENAI_API_KEY.

    Args:
        transcript: Raw text transcript from the job seeker.

    Returns:
        Dictionary conforming to the resume blob schema.

    Raises:
        ValueError: If the result is completely empty (no name or headline).
        httpx.HTTPStatusError: If the AI API returns an error.
        json.JSONDecodeError: If the response is not valid JSON.
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if openrouter_key:
        base_url = "https://openrouter.ai/api/v1"
        api_key = openrouter_key
        model = "openai/gpt-4o-mini"
    elif openai_key:
        base_url = "https://api.openai.com/v1"
        api_key = openai_key
        model = "gpt-4o-mini"
    else:
        raise ValueError("Either OPENROUTER_API_KEY or OPENAI_API_KEY is required for transcript structuring")

    messages = [
        {"role": "system", "content": _RESUME_VOICE_PROMPT},
        {"role": "user", "content": f"Speech transcript:\n\n{transcript}"},
    ]

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "max_tokens": 8000,
                "temperature": 0.1,
            },
        )
        response.raise_for_status()
        data = response.json()

    raw_content = data["choices"][0]["message"]["content"].strip()

    # Strip markdown code fences if the model wrapped the JSON
    if raw_content.startswith("```"):
        lines = raw_content.splitlines()
        # Remove first and last fence lines
        raw_content = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    result = json.loads(raw_content)

    # Ensure all required keys are present (fill missing with defaults)
    for key in _REQUIRED_KEYS:
        if key not in result:
            if key in ("experience", "education", "skills", "languages"):
                result[key] = []
            elif key == "contact":
                result[key] = {"email": "", "phone": "", "location": "", "linkedin": ""}
            else:
                result[key] = ""

    # Validate that at least name or headline is populated
    if not result.get("name") and not result.get("headline"):
        raise ValueError(
            "Transcript structuring produced an empty result: neither 'name' nor 'headline' was extracted. "
            "Please provide a more detailed transcript."
        )

    return result
