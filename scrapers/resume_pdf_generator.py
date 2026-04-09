"""
resume_pdf_generator.py — Professional ATS-friendly PDF resume generator
Uses reportlab. ATS-optimized: no tables, no images, no columns, black text only.
"""
import os
import hashlib
import logging
from typing import Optional
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

logger = logging.getLogger(__name__)
PDF_DIR = os.getenv("PDF_DIR", "/tmp/resumes")

# Russian + English section headers to detect
SECTION_HEADERS_RU = [
    "ОПЫТ РАБОТЫ", "ОБРАЗОВАНИЕ", "НАВЫКИ", "ТЕХНИЧЕСКИЕ НАВЫКИ",
    "ПРОФЕССИОНАЛЬНЫЕ НАВЫКИ", "О СЕБЕ", "КРАТКОЕ РЕЗЮМЕ", "SUMMARY",
    "EXPERIENCE", "EDUCATION", "SKILLS", "LANGUAGES", "ЯЗЫКИ",
    "ДОСТИЖЕНИЯ", "ACHIEVEMENTS", "СЕРТИФИКАТЫ", "CERTIFICATIONS",
    "ПРОЕКТЫ", "PROJECTS", "КОНТАКТЫ", "CONTACTS",
]


def _detect_sections(text: str) -> list:
    """
    Splits resume text into (header, body) tuples.
    Detects headers: lines that are ALL CAPS, or end with ':', or match SECTION_HEADERS_RU.
    Returns list of tuples like [("", "Иван Иванов\\nиван@email.com"), ("ОПЫТ РАБОТЫ", "..."), ...]
    First tuple has empty header (contact/name block).
    """
    lines = text.splitlines()
    sections: list = []
    current_header = ""
    current_body_lines: list = []

    def _is_header(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        # Match known section headers (normalized)
        normalized = stripped.upper().rstrip(":")
        if normalized in SECTION_HEADERS_RU:
            return True
        # All uppercase (and at least 3 chars, not a single word in normal text)
        if stripped.upper() == stripped and stripped.isalpha() is False and len(stripped) >= 3:
            # Allow all-caps lines that contain at least one letter
            if any(c.isalpha() for c in stripped) and stripped == stripped.upper():
                return True
        # Ends with colon and is short enough to be a header
        if stripped.endswith(":") and len(stripped) <= 60:
            return True
        return False

    first_header_found = False

    for line in lines:
        stripped = line.strip()
        if _is_header(stripped):
            # Save current accumulation
            body = "\n".join(current_body_lines).strip()
            if not first_header_found:
                # Everything before first header is contact/name block
                sections.append(("", body))
                first_header_found = True
            else:
                sections.append((current_header, body))
            current_header = stripped.rstrip(":")
            current_body_lines = []
        else:
            current_body_lines.append(line)

    # Flush last section
    body = "\n".join(current_body_lines).strip()
    if not first_header_found:
        # No headers found at all — entire text is one block
        sections.append(("", body))
    else:
        sections.append((current_header, body))

    return sections


def generate_resume_pdf(
    resume_text: str,
    candidate_name: str,
    user_id: int,
    vacancy_id: str,
) -> Optional[str]:
    """
    Creates /tmp/resumes/resume_{user_id}_{vacancy_id}.pdf
    Returns full path to PDF file, or None if reportlab is unavailable.
    """
    if not REPORTLAB_AVAILABLE:
        logger.warning(
            "[resume_pdf_generator] reportlab not installed — cannot generate PDF. "
            "Install with: pip install reportlab"
        )
        return None

    os.makedirs(PDF_DIR, exist_ok=True)

    # Sanitize vacancy_id for use in filename
    safe_vacancy_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(vacancy_id))
    pdf_path = os.path.join(PDF_DIR, f"resume_{user_id}_{safe_vacancy_id}.pdf")

    try:
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        # ── Styles ──────────────────────────────────────────────────────────
        name_style = ParagraphStyle(
            "NameStyle",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=4,
        )

        section_header_style = ParagraphStyle(
            "SectionHeaderStyle",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1a1a1a"),
            spaceBefore=10,
            spaceAfter=2,
        )

        body_style = ParagraphStyle(
            "BodyStyle",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=2,
        )

        # ── Build story ──────────────────────────────────────────────────────
        story = []

        # Name header
        safe_name = candidate_name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(safe_name, name_style))

        # Horizontal rule under name
        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#1a1a1a"),
            spaceAfter=8,
        ))

        # Parse sections
        sections = _detect_sections(resume_text)

        for header, body in sections:
            if header:
                # Section header
                safe_header = header.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                story.append(Paragraph(safe_header, section_header_style))
                # Thin border line under section header
                story.append(HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#888888"),
                    spaceAfter=4,
                ))

            if body:
                # Split body into paragraphs, emit each
                for para_text in body.split("\n"):
                    para_text = para_text.strip()
                    if not para_text:
                        story.append(Spacer(1, 4))
                        continue
                    safe_para = (
                        para_text
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    story.append(Paragraph(safe_para, body_style))

            # Spacer between sections
            if header:
                story.append(Spacer(1, 8))

        doc.build(story)
        logger.info("[resume_pdf_generator] PDF saved: %s", pdf_path)
        return pdf_path

    except Exception as exc:
        logger.exception("[resume_pdf_generator] Failed to generate PDF: %s", exc)
        return None


def cleanup_pdf(pdf_path: str) -> None:
    """Deletes file if exists, logs warning if not found."""
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
        logger.info("[resume_pdf_generator] Deleted PDF: %s", pdf_path)
    else:
        logger.warning("[resume_pdf_generator] cleanup_pdf: file not found: %s", pdf_path)


def get_pdf_path(user_id: int, vacancy_id: str) -> str:
    """Returns expected path without creating the file."""
    safe_vacancy_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(vacancy_id))
    return os.path.join(PDF_DIR, f"resume_{user_id}_{safe_vacancy_id}.pdf")
