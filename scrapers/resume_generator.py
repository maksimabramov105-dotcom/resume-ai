"""
resume_generator.py — AI-powered tailored resume generator
Calls OpenAI API to create resumes tailored to specific vacancies.
Also generates PDF using reportlab.
"""
import asyncio
import aiohttp
import logging
import os
import json
import hashlib
from typing import Optional, Tuple
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_LEFT, TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logging.warning(
        "[resume_generator] reportlab not installed. PDF generation disabled."
    )

logger = logging.getLogger(__name__)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"
RESUMES_TMP_DIR = "/tmp/resumes"


async def call_openai(
    prompt: str,
    system: str,
    api_key: str,
    max_tokens: int = 1500,
) -> str:
    """
    POST to OpenAI chat completions.
    Returns the assistant's message content string.
    Raises ValueError on auth errors, RuntimeError on other failures.
    """
    if not api_key:
        raise ValueError("[resume_generator] call_openai: api_key is empty")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENAI_API_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                        .strip()
                    )
                    logger.debug(
                        f"[resume_generator] call_openai success, len={len(content)}"
                    )
                    return content

                elif resp.status == 401:
                    text = await resp.text()
                    raise ValueError(
                        f"[resume_generator] OpenAI invalid API key (401): {text[:200]}"
                    )

                elif resp.status == 429:
                    text = await resp.text()
                    raise RuntimeError(
                        f"[resume_generator] OpenAI rate limited (429): {text[:200]}"
                    )

                elif resp.status == 400:
                    text = await resp.text()
                    raise ValueError(
                        f"[resume_generator] OpenAI bad request (400): {text[:300]}"
                    )

                else:
                    text = await resp.text()
                    raise RuntimeError(
                        f"[resume_generator] OpenAI HTTP {resp.status}: {text[:300]}"
                    )

    except asyncio.TimeoutError:
        raise RuntimeError(
            "[resume_generator] call_openai timed out after 60 seconds"
        )
    except aiohttp.ClientError as e:
        raise RuntimeError(
            f"[resume_generator] call_openai network error: {e}"
        )


async def generate_tailored_resume(
    user_profile: str,
    vacancy_description: str,
    vacancy_title: str,
    company_name: str,
    openai_api_key: str,
    language: str = "ru",
) -> str:
    """
    Generate a tailored resume using GPT-4o-mini.
    Returns resume as plain text (800-1200 words).
    Raises RuntimeError on failure.
    """
    lang_instruction = (
        "Write in Russian language."
        if language.lower() in ("ru", "russian")
        else "Write in English language."
    )

    system = (
        "You are an expert career consultant. "
        "Create a professional resume tailored to the specific job posting. "
        "Include relevant keywords from the vacancy for ATS optimization. "
        "Format as clean plain text with clear sections. "
        f"{lang_instruction}"
    )

    prompt = f"""Create a tailored professional resume for the following job posting.

JOB TITLE: {vacancy_title}
COMPANY: {company_name}

JOB DESCRIPTION:
{vacancy_description[:3000]}

CANDIDATE PROFILE:
{user_profile[:2000]}

Requirements:
- Length: 800-1200 words
- Include sections: Summary/Objective, Experience, Skills, Education
- Use keywords from the job description for ATS optimization
- Highlight the most relevant experience and skills for this specific role
- Professional tone and format
- Plain text only, no markdown symbols like ** or #

Write the complete resume now:"""

    logger.info(
        f"[resume_generator] generate_tailored_resume: "
        f"vacancy='{vacancy_title}' company='{company_name}'"
    )

    try:
        result = await asyncio.wait_for(
            call_openai(
                prompt=prompt,
                system=system,
                api_key=openai_api_key,
                max_tokens=1800,
            ),
            timeout=45,
        )
        logger.info(
            f"[resume_generator] generate_tailored_resume complete, len={len(result)}"
        )
        return result
    except asyncio.TimeoutError:
        raise RuntimeError(
            "[resume_generator] generate_tailored_resume timed out after 45 seconds"
        )


async def generate_cover_letter(
    user_profile: str,
    vacancy_description: str,
    company_name: str,
    openai_api_key: str,
    language: str = "ru",
) -> str:
    """
    Generate a tailored cover letter using GPT-4o-mini.
    Returns cover letter as plain text (200-300 words).
    Raises RuntimeError on failure.
    """
    lang_instruction = (
        "Write in Russian language."
        if language.lower() in ("ru", "russian")
        else "Write in English language."
    )

    system = (
        "You are an expert career consultant specializing in writing compelling cover letters. "
        "Create concise, personalized cover letters that highlight the candidate's fit. "
        "Be specific, professional, and enthusiastic. "
        f"{lang_instruction}"
    )

    prompt = f"""Write a concise professional cover letter for this job application.

COMPANY: {company_name}

JOB DESCRIPTION:
{vacancy_description[:2000]}

CANDIDATE PROFILE:
{user_profile[:1500]}

Requirements:
- Length: 200-300 words (keep it concise)
- Opening: Express interest and mention the specific role
- Body: Highlight 2-3 most relevant skills/experiences that match the job
- Closing: Call to action, express eagerness for interview
- Professional but personable tone
- Plain text only, no markdown

Write the cover letter now:"""

    logger.info(
        f"[resume_generator] generate_cover_letter: company='{company_name}'"
    )

    try:
        result = await asyncio.wait_for(
            call_openai(
                prompt=prompt,
                system=system,
                api_key=openai_api_key,
                max_tokens=600,
            ),
            timeout=45,
        )
        logger.info(
            f"[resume_generator] generate_cover_letter complete, len={len(result)}"
        )
        return result
    except asyncio.TimeoutError:
        raise RuntimeError(
            "[resume_generator] generate_cover_letter timed out after 45 seconds"
        )


def generate_resume_pdf(
    resume_text: str,
    candidate_name: str,
    output_path: str,
) -> Optional[str]:
    """
    Generate a clean PDF from resume plain text using reportlab.
    Creates /tmp/resumes/ directory if needed.
    Returns output_path on success, None if reportlab is not available or on error.
    """
    if not REPORTLAB_AVAILABLE:
        logger.warning(
            "[resume_generator] generate_resume_pdf: reportlab not available"
        )
        return None

    try:
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        else:
            os.makedirs(RESUMES_TMP_DIR, exist_ok=True)
            output_path = os.path.join(RESUMES_TMP_DIR, os.path.basename(output_path))

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CandidateTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            spaceAfter=6,
            alignment=TA_CENTER,
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            spaceBefore=12,
            spaceAfter=4,
            alignment=TA_LEFT,
        )
        body_style = ParagraphStyle(
            "BodyText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            spaceAfter=4,
            alignment=TA_LEFT,
        )

        story = []

        # Candidate name as title
        if candidate_name:
            story.append(Paragraph(candidate_name, title_style))
            story.append(Spacer(1, 0.3 * cm))

        # Parse resume text into sections
        lines = resume_text.split("\n")
        current_section_lines = []

        SECTION_KEYWORDS = (
            "опыт", "образование", "навыки", "summary", "experience",
            "education", "skills", "objective", "о себе", "достижения",
            "achievements", "languages", "языки", "контакты", "contacts",
        )

        def flush_section(lines_buf):
            for line in lines_buf:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 0.15 * cm))
                    continue
                # Detect section headers: ALL CAPS or known keywords
                is_header = (
                    line.isupper() and len(line) > 3
                    or any(kw in line.lower() for kw in SECTION_KEYWORDS)
                    and len(line) < 60
                )
                if is_header:
                    story.append(Paragraph(line, section_style))
                else:
                    # Escape XML characters for reportlab
                    safe_line = (
                        line
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    story.append(Paragraph(safe_line, body_style))

        flush_section(lines)

        doc.build(story)
        logger.info(
            f"[resume_generator] generate_resume_pdf: saved to {output_path}"
        )
        return output_path

    except Exception as e:
        logger.exception(f"[resume_generator] generate_resume_pdf error: {e}")
        return None


def get_resume_cache_key(user_profile: str, company_type: str) -> str:
    """
    Generate a cache key (MD5 hash) for a user profile + company type combination.
    Useful for caching generated resumes.
    """
    raw = f"{user_profile.strip()}::{company_type.strip().lower()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def build_output_path(candidate_name: str, vacancy_title: str, suffix: str = "") -> str:
    """
    Build a safe output file path for a resume PDF.
    Saves to RESUMES_TMP_DIR.
    """
    os.makedirs(RESUMES_TMP_DIR, exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in candidate_name)
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in vacancy_title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"resume_{safe_name}_{safe_title}_{timestamp}{suffix}.pdf"
    return os.path.join(RESUMES_TMP_DIR, filename)
