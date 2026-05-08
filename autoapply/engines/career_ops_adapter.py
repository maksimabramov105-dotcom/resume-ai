"""
autoapply/engines/career_ops_adapter.py — career-ops quality engine adapter.

Integrates vendor/career-ops (santifer/career-ops@8e554cc) as a parallel
autoapply engine for portal-based applications (Greenhouse, Ashby, Lever,
Wellfound, company career pages).

Design:
- Scoring uses OpenAI/OpenRouter directly (oferta-mode logic).
- PDF generation uses `node vendor/career-ops/generate-pdf.mjs`.
- HITL: applications land in status='pending_review'; the user reviews and
  clicks Submit in the dashboard, which calls ATSFiller to do the final apply.
- Secrets isolation: adapter strips linkedin_password_enc before writing
  any portfolio file that career-ops or the sidecar process reads.
- Country gate: applied before any processing (same gate as api_boards).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from typing import Optional

from autoapply.country_gate import is_allowed_jurisdiction, resolve_company_country

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAREER_OPS_DIR = os.path.join(ROOT, "vendor", "career-ops")
CV_STORE_DIR = os.path.join(os.getenv("CAREER_OPS_CV_DIR", "/opt/resumeaibot/cv"))
MIN_SCORE_FOR_PDF = float(os.getenv("CAREER_OPS_MIN_SCORE", "5.5"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ── Secrets-safe public portfolio ─────────────────────────────────────────────

_SECRET_COLUMNS = {"linkedin_password_enc", "password_hash", "hh_token"}


def _public_portfolio(user: dict) -> dict:
    """Return user dict with all secret columns stripped."""
    return {k: v for k, v in user.items() if k not in _SECRET_COLUMNS}


# ── Scoring (oferta-mode logic via OpenAI) ────────────────────────────────────

_SCORE_SYSTEM = """\
You are an expert recruiter and career coach. Evaluate how well a candidate's
profile matches a job description. Return ONLY valid JSON (no markdown).
"""

_SCORE_USER_TMPL = """\
Job title: {title}
Company: {company}
Job description:
{description}

Candidate resume summary:
{resume_summary}

Score this match on 6 dimensions (0.0–10.0 each), then compute a weighted average:
  skills_match       weight 0.30
  seniority_fit      weight 0.20
  role_alignment     weight 0.20
  location_fit       weight 0.10
  industry_fit       weight 0.10
  growth_potential   weight 0.10

Return JSON exactly:
{{
  "dimensions": {{
    "skills_match": <float>,
    "seniority_fit": <float>,
    "role_alignment": <float>,
    "location_fit": <float>,
    "industry_fit": <float>,
    "growth_potential": <float>
  }},
  "composite_score": <float 0-10>,
  "top_strengths": [<str>, <str>],
  "key_gaps": [<str>],
  "one_line_summary": "<str>"
}}
"""


async def score_vacancy(vacancy: dict, portfolio: dict) -> dict:
    """
    Score a single vacancy against the candidate portfolio.
    Implements the career-ops oferta-mode evaluation logic.
    Returns a score dict with composite_score (0-10) and dimensions.
    Falls back to a neutral 5.0 score on any error.
    """
    resume_text = portfolio.get("resume_text") or ""
    resume_summary = resume_text[:1500] if resume_text else "(no resume provided)"
    job_title = vacancy.get("title", "")
    company = vacancy.get("company", "")
    description = (vacancy.get("description") or "")[:3000]

    prompt = _SCORE_USER_TMPL.format(
        title=job_title,
        company=company,
        description=description,
        resume_summary=resume_summary,
    )

    try:
        raw = await _call_openai(system=_SCORE_SYSTEM, user=prompt, max_tokens=512)
        data = json.loads(raw)
        score = float(data.get("composite_score", 5.0))
        data["composite_score"] = max(0.0, min(10.0, score))
        return data
    except Exception as exc:
        logger.warning("[career_ops] score_vacancy error: %s", exc)
        return {
            "composite_score": 5.0,
            "dimensions": {},
            "top_strengths": [],
            "key_gaps": [],
            "one_line_summary": "Score unavailable",
        }


async def _call_openai(system: str, user: str, max_tokens: int = 512) -> str:
    """OpenRouter-first, OpenAI fallback. Returns raw text response."""
    import aiohttp

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    # Try OpenRouter first
    if OPENROUTER_API_KEY:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://resumeai-bot.ru",
                    },
                    json={
                        "model": "anthropic/claude-haiku-3-5",
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": 0.2,
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        d = await resp.json()
                        return d["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.debug("[career_ops] openrouter error, falling back: %s", exc)

    # OpenAI fallback
    if OPENAI_API_KEY:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                resp.raise_for_status()
                d = await resp.json()
                return d["choices"][0]["message"]["content"].strip()

    raise RuntimeError("No AI API key configured (OPENROUTER_API_KEY or OPENAI_API_KEY)")


# ── PDF generation ────────────────────────────────────────────────────────────

_CV_HTML_TMPL = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: 'DM Sans', Arial, sans-serif; font-size: 11px;
          line-height: 1.5; color: #1a1a1a; margin: 0; padding: 32px 40px; }}
  h1 {{ font-family: 'Space Grotesk', Arial, sans-serif; font-size: 22px;
        font-weight: 700; margin: 0 0 4px; }}
  .contact {{ font-size: 10px; color: #555; margin-bottom: 16px; }}
  .divider {{ height: 2px; background: linear-gradient(to right,
              hsl(187,74%,32%), hsl(270,70%,45%)); margin-bottom: 16px; }}
  h2 {{ font-family: 'Space Grotesk', Arial, sans-serif; font-size: 11px;
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
        color: hsl(187,74%,32%); margin: 14px 0 6px; }}
  p, li {{ margin: 0 0 4px; white-space: pre-wrap; }}
  ul {{ margin: 0; padding-left: 16px; }}
  .score-badge {{ font-size: 9px; color: #888;
                  border: 1px solid #ccc; border-radius: 4px;
                  padding: 1px 5px; float: right; margin-top: 2px; }}
</style>
</head>
<body>
  <h1>{candidate_name}</h1>
  <span class="score-badge">Match: {match_score:.1f}/10</span>
  <div class="contact">{contact_line}</div>
  <div class="divider"></div>
  <h2>Match Summary</h2>
  <p>{one_line_summary}</p>
  <h2>Profile</h2>
  <p>{resume_text}</p>
</body>
</html>
"""


def _build_cv_html(portfolio: dict, score_result: dict, vacancy: dict) -> str:
    """Assemble a simple ATS-ready HTML CV from the public portfolio + score."""
    name = (portfolio.get("full_name") or portfolio.get("email") or "Candidate").strip()
    email = portfolio.get("email") or ""
    resume_text = (portfolio.get("resume_text") or "")[:4000]
    match_score = score_result.get("composite_score", 5.0)
    one_line = score_result.get("one_line_summary", "")
    company = vacancy.get("company", "")

    contact_parts = [p for p in [email] if p]
    contact_line = " · ".join(contact_parts) if contact_parts else ""

    return _CV_HTML_TMPL.format(
        candidate_name=name,
        contact_line=contact_line,
        match_score=match_score,
        one_line_summary=one_line,
        resume_text=resume_text,
        company=company,
    )


async def generate_cv_pdf(
    cv_html: str,
    user_id: int,
    company_slug: str,
    job_id: str,
) -> Optional[str]:
    """
    Write HTML to a temp file, invoke career-ops generate-pdf.mjs via Node.js,
    move output to CV_STORE_DIR/<user_id>/<job_id>.pdf, return path.
    Falls back to None if Node.js / Playwright is unavailable.
    """
    node_bin = shutil.which("node")
    if not node_bin:
        logger.warning("[career_ops] node not found — PDF generation skipped")
        return None

    # Ensure output directory exists (only after confirming node is available)
    user_cv_dir = os.path.join(CV_STORE_DIR, str(user_id))
    os.makedirs(user_cv_dir, exist_ok=True)

    pdf_filename = f"{company_slug}-{job_id}.pdf"
    output_path = os.path.join(user_cv_dir, pdf_filename)

    generate_script = os.path.join(CAREER_OPS_DIR, "generate-pdf.mjs")
    if not os.path.isfile(generate_script):
        logger.warning("[career_ops] generate-pdf.mjs not found at %s", generate_script)
        return None

    with tempfile.NamedTemporaryFile(
        suffix=".html", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(cv_html)
        html_path = f.name

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            [node_bin, generate_script, html_path, output_path, "--format=a4"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=CAREER_OPS_DIR,
        )
        if result.returncode != 0:
            logger.warning(
                "[career_ops] generate-pdf.mjs failed (rc=%d): %s",
                result.returncode, result.stderr[:300],
            )
            return None
        logger.info("[career_ops] PDF generated: %s", output_path)
        return output_path
    except Exception as exc:
        logger.warning("[career_ops] generate_cv_pdf error: %s", exc)
        return None
    finally:
        try:
            os.unlink(html_path)
        except OSError:
            pass


# ── Batch runner ──────────────────────────────────────────────────────────────

async def run_batch(
    campaign: dict,
    vacancies: list[dict],
    user: dict,
    db_path: str | None = None,
) -> list[dict]:
    """
    Process a batch of vacancies through the career-ops quality engine.

    For each vacancy that:
      1. Passes the country gate (same blocklist as api_boards engine)
      2. Has not been applied to before
      3. Scores >= MIN_SCORE_FOR_PDF (default 5.5 / 10)

    We:
      a. Score it against the candidate portfolio (oferta mode)
      b. Build a tailored CV HTML
      c. Generate a PDF via career-ops generate-pdf.mjs
      d. Insert an application row with status='pending_review' and cv_pdf_path
      e. Return the list of created application dicts

    The HITL review step (user clicks Submit in the dashboard) is handled by
    POST /api/applications/{id}/review in autoapply_main.py.
    """
    from autoapply.config import AUTOAPPLY_DB as _DB
    from autoapply.autoapply_db import (
        is_vacancy_applied,
        log_application,
        get_application_by_id,
    )

    db = db_path or _DB
    campaign_id = campaign["id"]
    user_id = user["id"]
    # Strip secrets before passing to PDF / scoring functions
    public_portfolio = _public_portfolio(user)

    results: list[dict] = []

    for vacancy in vacancies:
        if not isinstance(vacancy, dict):
            continue

        vacancy_id = str(vacancy.get("id") or vacancy.get("vacancy_id", ""))
        if not vacancy_id:
            continue

        # Country gate — must come first
        company_country = resolve_company_country(vacancy)
        if not is_allowed_jurisdiction(company_country):
            logger.info(
                "[career_ops] blocked vacancy=%s company=%r country=%s",
                vacancy_id, vacancy.get("company"), company_country,
            )
            continue

        # Skip already processed
        already = await is_vacancy_applied(vacancy_id, user_id, db)
        if already:
            continue

        # Score against portfolio
        score_result = await score_vacancy(vacancy, public_portfolio)
        composite = score_result.get("composite_score", 0.0)

        if composite < MIN_SCORE_FOR_PDF:
            logger.info(
                "[career_ops] vacancy=%s score=%.1f < %.1f threshold — skipped",
                vacancy_id, composite, MIN_SCORE_FOR_PDF,
            )
            continue

        # Build & generate PDF
        cv_html = _build_cv_html(public_portfolio, score_result, vacancy)
        company_slug = _slugify(vacancy.get("company", "unknown"))
        job_slug = _slugify(vacancy.get("title", "job"))
        cv_pdf_path = await generate_cv_pdf(
            cv_html=cv_html,
            user_id=user_id,
            company_slug=company_slug,
            job_id=f"{job_slug}-{vacancy_id[:8]}",
        )

        # Log as pending_review
        try:
            app_id = await log_application(
                campaign_id=campaign_id,
                user_id=user_id,
                platform="career_ops",
                vacancy_id=vacancy_id,
                vacancy_title=vacancy.get("title", ""),
                company_name=vacancy.get("company", ""),
                vacancy_url=vacancy.get("url", ""),
                resume_used=public_portfolio.get("resume_text", "")[:500],
                company_country=company_country,
                engine="career_ops",
                cv_pdf_path=cv_pdf_path,
                match_score=composite,
                status="pending_review",
                db_path=db,
            )
            results.append({
                "application_id": app_id,
                "vacancy_id": vacancy_id,
                "vacancy_title": vacancy.get("title", ""),
                "company_name": vacancy.get("company", ""),
                "match_score": composite,
                "cv_pdf_path": cv_pdf_path,
                "status": "pending_review",
            })
            logger.info(
                "[career_ops] pending_review app_id=%s vacancy=%s score=%.1f cv=%s",
                app_id, vacancy_id, composite, cv_pdf_path or "(no pdf)",
            )
        except Exception as exc:
            logger.exception("[career_ops] log_application error: %s", exc)

    return results


async def submit_application(
    application_id: int,
    user: dict,
    db_path: str | None = None,
) -> dict:
    """
    HITL submit step — called from POST /api/applications/{id}/review.

    Reads the application row, attempts to fill the ATS form via ATSFiller,
    updates status to 'sent' on success or 'failed' on error.
    The ATSFiller does the actual portal submit; career-ops design intent
    (HITL) is preserved because the user triggered this explicitly.
    """
    from autoapply.config import AUTOAPPLY_DB as _DB
    from autoapply.autoapply_db import (
        get_application_by_id,
        update_application_after_review,
    )

    db = db_path or _DB
    app = await get_application_by_id(application_id, user["id"], db)
    if not app:
        return {"ok": False, "detail": "Application not found"}
    if app.get("status") != "pending_review":
        return {"ok": False, "detail": f"Application status is '{app.get('status')}', expected 'pending_review'"}

    apply_url = app.get("vacancy_url", "")
    public_portfolio = _public_portfolio(user)
    resume_text = public_portfolio.get("resume_text", "")

    user_data = {
        "first_name": (public_portfolio.get("full_name") or "").split()[0] or "",
        "last_name": " ".join((public_portfolio.get("full_name") or "").split()[1:]) or "",
        "email": public_portfolio.get("email", ""),
        "phone": public_portfolio.get("phone", ""),
        "linkedin": public_portfolio.get("linkedin_url", ""),
        "resume_text": resume_text,
        "cover_letter": resume_text[:500],
    }

    ats_success = False
    if apply_url and user_data["email"]:
        try:
            from autoapply.ats_filler import ATSFiller
            filler = ATSFiller(headless=True)
            await filler.start()
            try:
                ats_success = await filler.apply(apply_url, user_data)
            finally:
                await filler.close()
        except ImportError:
            logger.debug("[career_ops] ats_filler not available")
        except Exception as exc:
            logger.warning("[career_ops] submit ats_filler error url=%s: %s", apply_url, exc)

    new_status = "sent" if ats_success else "queued"
    updated = await update_application_after_review(application_id, user["id"], new_status, db)
    if not updated:
        return {"ok": False, "detail": "Could not update application status"}

    return {
        "ok": True,
        "application_id": application_id,
        "status": new_status,
        "ats_submitted": ats_success,
    }


# ── Utilities ─────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    import re
    t = text.lower().strip()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t[:40].strip("-") or "unknown"
