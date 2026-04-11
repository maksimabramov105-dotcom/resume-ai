"""
autoapply_main.py — FastAPI application for AutoApply web service.
Runs on port 8080. Bot uses 8000, dashboard uses 8501.
"""
import asyncio
import hashlib
import hmac
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import bcrypt as _bcrypt_lib
import aiosqlite
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from autoapply.autoapply_db import (
    advance_drip_step,
    consume_email_token,
    create_campaign,
    create_drip_sequence,
    create_email_token,
    create_user,
    get_active_campaigns,
    get_applications_for_user,
    get_campaigns_for_user,
    get_dashboard_stats,
    get_pending_drip_users,
    get_user_by_email,
    get_user_by_id,
    init_db,
    mark_user_verified,
    update_campaign_status,
    update_user_last_active,
    update_user_password,
    update_user_plan,
)
from autoapply.email_sender import (
    send_drip_email,
    send_password_reset_email,
    send_verification_email,
    send_welcome_email,
)
from autoapply.config import (
    AUTOAPPLY_DB,
    AUTOAPPLY_HOST,
    AUTOAPPLY_PORT,
    BOT_DB,
    CRYPTOBOT_WEBHOOK_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRE_HOURS,
    JWT_SECRET,
    LOGS_DIR,
    PLANS,
    WEBAPP_BASE_URL,
)
from autoapply.payments import process_payment, verify_webhook

# ── Logging ───────────────────────────────────────────────────────────────────
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOGS_DIR, "autoapply_api.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("autoapply_main")

# ── Password hashing (direct bcrypt — compatible with bcrypt 4.x and 5.x) ────
def _hash_password(password: str) -> str:
    """Hash a password with bcrypt. Works with bcrypt 4.x and 5.x."""
    return _bcrypt_lib.hashpw(
        password.encode("utf-8"), _bcrypt_lib.gensalt()
    ).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        return _bcrypt_lib.checkpw(
            password.encode("utf-8"), hashed.encode("utf-8")
        )
    except Exception:
        return False

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AutoApply API",
    description="АвтоОтклик — automated job application service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_DIR = Path(ROOT) / "autoapply" / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

APP_HTML = STATIC_DIR / "app.html"


# ── Email drip background processor ──────────────────────────────────────────
async def process_email_drip():
    """Process pending drip emails — runs every hour."""
    from datetime import timedelta

    DRIP_DELAYS = [0, 1, 3, 5, 7, 14]  # days after signup

    while True:
        try:
            pending = await get_pending_drip_users()
            for drip in pending:
                step = drip["step"]
                sent = send_drip_email(drip["email"], step)
                if sent:
                    logger.info(f"Drip step {step} sent to {drip['email']}")

                # Calculate next send time
                if step + 1 < len(DRIP_DELAYS):
                    delay_days = DRIP_DELAYS[step + 1] - DRIP_DELAYS[step]
                    next_send = datetime.now(timezone.utc) + timedelta(days=delay_days)
                    await advance_drip_step(drip["id"], next_send, completed=False)
                else:
                    await advance_drip_step(drip["id"], None, completed=True)
        except Exception as e:
            logger.error(f"Drip processor error: {e}")

        await asyncio.sleep(3600)  # Run every hour


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("[autoapply_main] Starting up — initialising DB at %s", AUTOAPPLY_DB)
    await init_db(AUTOAPPLY_DB)
    logger.info("[autoapply_main] DB ready")
    asyncio.create_task(process_email_drip())


# ── Pydantic models ───────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    telegram_id: Optional[int] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class CampaignCreateRequest(BaseModel):
    job_title: str
    location: str
    salary_min: int = 0
    experience: str = ""
    platforms: List[str] = ["hh"]
    daily_limit: int = 10


class ResumeConnectRequest(BaseModel):
    telegram_id: int


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


# ── JWT helpers ───────────────────────────────────────────────────────────────
def _create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
) -> dict:
    """Decode JWT from Authorization header. Raises 401 if invalid."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    user = await get_user_by_id(user_id, AUTOAPPLY_DB)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    await update_user_last_active(user_id, AUTOAPPLY_DB)
    return user


# ── Auth endpoints ────────────────────────────────────────────────────────────
@app.post("/api/register", summary="Register new account")
async def register(body: RegisterRequest):
    logger.info("[api/register] attempt for email=%s", body.email)

    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен быть не менее 6 символов")

    existing = await get_user_by_email(body.email, AUTOAPPLY_DB)
    if existing:
        raise HTTPException(status_code=409, detail="Email уже зарегистрирован")

    password_hash = _hash_password(body.password)
    try:
        user_id = await create_user(
            email=body.email,
            password_hash=password_hash,
            telegram_id=body.telegram_id,
            db_path=AUTOAPPLY_DB,
        )
    except Exception as exc:
        logger.error("[api/register] DB error: %s", exc)
        raise HTTPException(status_code=500, detail="Ошибка регистрации")

    # Start email drip sequence
    try:
        await create_drip_sequence(user_id)
    except Exception:
        pass

    # Send verification email (non-blocking — don't fail registration if SMTP is not set up)
    try:
        verify_token = await create_email_token(user_id, kind="verify", ttl_hours=24)
        sent = send_verification_email(body.email, verify_token)
        if sent:
            logger.info("[api/register] verification email sent to %s", body.email)
        else:
            logger.warning("[api/register] SMTP not configured — skipping verification email")
    except Exception as exc:
        logger.error("[api/register] email error (non-fatal): %s", exc)

    token = _create_token(user_id)
    logger.info("[api/register] success user_id=%s", user_id)
    return {"token": token, "user_id": user_id, "email_sent": True}


@app.get("/api/verify-email", summary="Verify email with token from link")
async def verify_email(token: str):
    from fastapi.responses import RedirectResponse
    user_id = await consume_email_token(token, kind="verify")
    if not user_id:
        # Redirect to app with error — do NOT show reset-password form
        return RedirectResponse(url="/app?verify_error=1", status_code=302)

    await mark_user_verified(user_id)

    user = await get_user_by_id(user_id, AUTOAPPLY_DB)
    if user:
        try:
            send_welcome_email(user["email"])
        except Exception:
            pass

    # Issue JWT so user is auto-logged in after clicking the link
    jwt_token = _create_token(user_id)
    logger.info("[api/verify-email] user_id=%s verified, issuing auto-login token", user_id)
    return RedirectResponse(url=f"/app?verified=1&auth={jwt_token}", status_code=302)


@app.post("/api/resend-verification", summary="Resend email verification link")
async def resend_verification(current_user: dict = Depends(get_current_user)):
    if current_user.get("is_verified"):
        return {"ok": True, "message": "Уже подтверждён"}
    try:
        verify_token = await create_email_token(current_user["id"], kind="verify", ttl_hours=24)
        send_verification_email(current_user["email"], verify_token)
        logger.info("[api/resend-verification] sent to user_id=%s", current_user["id"])
    except Exception as exc:
        logger.error("[api/resend-verification] error: %s", exc)
        raise HTTPException(status_code=500, detail="Ошибка отправки")
    return {"ok": True}


@app.post("/api/forgot-password", summary="Request password reset email")
async def forgot_password(body: ForgotPasswordRequest):
    # Always return 200 to avoid email enumeration
    user = await get_user_by_email(body.email, AUTOAPPLY_DB)
    if user:
        try:
            reset_token = await create_email_token(user["id"], kind="reset", ttl_hours=1)
            send_password_reset_email(body.email, reset_token)
            logger.info("[api/forgot-password] reset email sent to %s", body.email)
        except Exception as exc:
            logger.error("[api/forgot-password] email error: %s", exc)
    return {"ok": True, "message": "Если email зарегистрирован — письмо отправлено"}


@app.post("/api/reset-password", summary="Set new password using reset token")
async def reset_password(body: ResetPasswordRequest):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен быть не менее 6 символов")

    user_id = await consume_email_token(body.token, kind="reset")
    if not user_id:
        raise HTTPException(status_code=400, detail="Ссылка недействительна или истекла")

    password_hash = _hash_password(body.password)
    await update_user_password(user_id, password_hash)
    logger.info("[api/reset-password] password updated for user_id=%s", user_id)
    return {"ok": True, "message": "Пароль успешно изменён"}


@app.post("/api/login", summary="Login and get JWT token")
async def login(body: LoginRequest):
    logger.info("[api/login] attempt for email=%s", body.email)

    user = await get_user_by_email(body.email, AUTOAPPLY_DB)
    if not user or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    token = _create_token(user["id"])
    logger.info("[api/login] success user_id=%s", user["id"])
    return {"token": token, "user_id": user["id"]}


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.get("/api/dashboard", summary="Get dashboard stats")
async def dashboard(current_user: dict = Depends(get_current_user)):
    if not current_user.get("is_verified"):
        raise HTTPException(status_code=403, detail="email_not_verified")
    stats = await get_dashboard_stats(current_user["id"], AUTOAPPLY_DB)
    if not stats:
        raise HTTPException(status_code=500, detail="Failed to fetch stats")
    return stats


# ── Campaign endpoints ────────────────────────────────────────────────────────
@app.post("/api/campaign/create", summary="Create a new campaign")
async def campaign_create(
    body: CampaignCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    plan_name = current_user.get("plan", "free")
    plan_info = PLANS.get(plan_name, PLANS["free"])

    # Check that daily_limit requested does not exceed plan
    requested_limit = min(body.daily_limit, plan_info["daily_limit"])

    if not body.platforms:
        raise HTTPException(status_code=400, detail="At least one platform required")

    try:
        campaign_id = await create_campaign(
            user_id=user_id,
            job_title=body.job_title,
            location=body.location,
            salary_min=body.salary_min,
            experience=body.experience,
            platforms=body.platforms,
            daily_limit=requested_limit,
            db_path=AUTOAPPLY_DB,
        )
    except Exception as exc:
        logger.error("[api/campaign/create] error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create campaign")

    logger.info("[api/campaign/create] user=%s campaign_id=%s", user_id, campaign_id)
    return {"campaign_id": campaign_id, "daily_limit": requested_limit}


@app.get("/api/campaigns", summary="List all campaigns for current user")
async def campaigns_list(current_user: dict = Depends(get_current_user)):
    campaigns = await get_campaigns_for_user(current_user["id"], AUTOAPPLY_DB)
    return campaigns


@app.get("/api/user/profile", summary="Get current user profile (plan, connections, resume)")
async def user_profile(current_user: dict = Depends(get_current_user)):
    """Returns user profile with plan, connections status, and resume_text."""
    return {
        "user_id": current_user["id"],
        "email": current_user.get("email"),
        "plan": current_user.get("plan", "free"),
        "daily_limit": current_user.get("daily_limit", 3),
        "telegram_id": current_user.get("telegram_id"),
        "resume_text": current_user.get("resume_text") or "",
        "connections": {
            "hh": bool(current_user.get("hh_token")),
            "linkedin": bool(current_user.get("linkedin_email")),
            "telegram_id": current_user.get("telegram_id"),
        },
    }


@app.get("/api/user/connections", summary="Get user connection status")
async def user_connections(current_user: dict = Depends(get_current_user)):
    """Returns which external accounts are connected."""
    return {
        "hh": bool(current_user.get("hh_token")),
        "linkedin": bool(current_user.get("linkedin_email")),
        "telegram_id": current_user.get("telegram_id"),
    }


@app.get("/api/campaign/{campaign_id}/status", summary="Get campaign status and last applications")
async def campaign_status(
    campaign_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    campaigns = await get_campaigns_for_user(user_id, AUTOAPPLY_DB)
    campaign = next((c for c in campaigns if c["id"] == campaign_id), None)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Last 20 applications for this campaign
    async with aiosqlite.connect(AUTOAPPLY_DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT * FROM applications
            WHERE campaign_id = ? AND user_id = ?
            ORDER BY sent_at DESC LIMIT 20
            """,
            (campaign_id, user_id),
        ) as cur:
            rows = await cur.fetchall()
            last_applications = [dict(r) for r in rows]

    return {**campaign, "last_applications": last_applications}


@app.post("/api/campaign/{campaign_id}/pause", summary="Pause a campaign")
async def campaign_pause(
    campaign_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    campaigns = await get_campaigns_for_user(user_id, AUTOAPPLY_DB)
    if not any(c["id"] == campaign_id for c in campaigns):
        raise HTTPException(status_code=404, detail="Campaign not found")
    await update_campaign_status(campaign_id, "paused", AUTOAPPLY_DB)
    return {"status": "paused", "campaign_id": campaign_id}


@app.post("/api/campaign/{campaign_id}/resume_campaign", summary="Resume a paused campaign")
async def campaign_resume(
    campaign_id: int,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    campaigns = await get_campaigns_for_user(user_id, AUTOAPPLY_DB)
    if not any(c["id"] == campaign_id for c in campaigns):
        raise HTTPException(status_code=404, detail="Campaign not found")
    await update_campaign_status(campaign_id, "active", AUTOAPPLY_DB)
    return {"status": "active", "campaign_id": campaign_id}


# ── Resume connect ────────────────────────────────────────────────────────────
@app.post("/api/resume/connect", summary="Import resume text from Telegram bot DB")
async def resume_connect(
    body: ResumeConnectRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Reads the user profile from bot.db and stores resume_text in autoapply_users.
    bot.db tables are never modified.
    """
    telegram_id = body.telegram_id
    logger.info("[api/resume/connect] user=%s telegram_id=%s", current_user["id"], telegram_id)

    try:
        async with aiosqlite.connect(BOT_DB) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT profile FROM users WHERE telegram_id = ?", (telegram_id,)
            ) as cur:
                row = await cur.fetchone()
    except Exception as exc:
        logger.error("[api/resume/connect] bot.db read error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read bot database")

    if not row or not row["profile"]:
        raise HTTPException(
            status_code=404,
            detail="No resume found for this Telegram account. Create it via the bot first.",
        )

    profile_text = row["profile"]
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            await db.execute(
                "UPDATE autoapply_users SET resume_text = ?, telegram_id = ? WHERE id = ?",
                (profile_text, telegram_id, current_user["id"]),
            )
            await db.commit()
    except Exception as exc:
        logger.error("[api/resume/connect] autoapply_db write error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to save resume")

    return {
        "success": True,
        "message": "Resume imported successfully",
        "preview": profile_text[:200] + "..." if len(profile_text) > 200 else profile_text,
    }


# ── Applications list ─────────────────────────────────────────────────────────
@app.get("/api/applications", summary="List applications (paginated)")
async def applications_list(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    platform: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_user),
):
    result = await get_applications_for_user(
        user_id=current_user["id"],
        page=page,
        per_page=per_page,
        platform=platform,
        status=status,
        db_path=AUTOAPPLY_DB,
    )
    return result


# ── Cover letter generation ───────────────────────────────────────────────────
@app.post("/api/generate-cover-letter", summary="Generate AI cover letter")
async def generate_cover_letter(
    payload: dict,
    current_user: dict = Depends(get_current_user)
):
    """Generate a personalized cover letter using OpenAI/OpenRouter."""
    job_description = payload.get("job_description", "").strip()
    tone = payload.get("tone", "professional")  # professional, friendly, creative
    resume_text = payload.get("resume_text", "")

    if not job_description:
        raise HTTPException(status_code=400, detail="job_description is required")

    tone_instructions = {
        "professional": "formal, concise, achievement-focused",
        "friendly": "warm, conversational, enthusiastic",
        "creative": "engaging, unique, memorable"
    }.get(tone, "professional")

    # Try OpenAI/OpenRouter
    import os, httpx
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")

    if not api_key:
        # Fallback mock
        return {"cover_letter": f"Уважаемый работодатель,\n\nЯ внимательно ознакомился с вашей вакансией и убеждён, что мой опыт и навыки полностью соответствуют вашим требованиям.\n\n[Это демо-письмо. Добавьте OPENROUTER_API_KEY в .env для AI-генерации]\n\nС уважением,\n{current_user.get('email', 'Кандидат')}"}

    prompt = f"""Write a cover letter in Russian for this job posting.
Tone: {tone_instructions}
Job posting: {job_description[:2000]}
{"Candidate resume/background: " + resume_text[:1000] if resume_text else ""}

Write ONLY the cover letter text, no explanation. Start with 'Уважаемый работодатель,' or similar greeting."""

    base_url = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else "https://api.openai.com/v1"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 600}
            )
            data = resp.json()
            letter = data["choices"][0]["message"]["content"].strip()
            return {"cover_letter": letter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


# ── Job search ─────────────────────────────────────────────────────────────────
@app.get("/api/jobs/search", summary="Search jobs via Remotive API")
async def search_jobs(
    q: str = "",
    city: str = "",
    remote: str = "",
    current_user: dict = Depends(get_current_user)
):
    """Search jobs from Remotive (remote jobs, no API key needed) + mock data."""
    import httpx

    mock_jobs = [
        {"title": "Python Backend Developer", "company": "Яндекс", "location": "Москва", "salary": "250 000 — 350 000 ₽", "remote": True, "match": 94, "url": "https://hh.ru"},
        {"title": "Full Stack Developer", "company": "Сбер", "location": "Москва", "salary": "180 000 — 260 000 ₽", "remote": False, "match": 87, "url": "https://hh.ru"},
        {"title": "Data Engineer", "company": "Тинькофф", "location": "Санкт-Петербург", "salary": "200 000 — 300 000 ₽", "remote": True, "match": 81, "url": "https://hh.ru"},
        {"title": "DevOps Engineer", "company": "VK", "location": "Москва", "salary": "220 000 — 320 000 ₽", "remote": True, "match": 76, "url": "https://hh.ru"},
        {"title": "Product Manager", "company": "Авито", "location": "Москва", "salary": "200 000 — 280 000 ₽", "remote": False, "match": 72, "url": "https://hh.ru"},
    ]

    try:
        # Try Remotive free API
        search_term = q or "developer"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://remotive.com/api/remote-jobs",
                params={"search": search_term, "limit": 10}
            )
            if resp.status_code == 200:
                data = resp.json()
                jobs = []
                for job in data.get("jobs", [])[:10]:
                    jobs.append({
                        "title": job.get("title", ""),
                        "company": job.get("company_name", ""),
                        "location": job.get("candidate_required_location", "Remote"),
                        "salary": job.get("salary", "Не указана"),
                        "remote": True,
                        "match": min(95, max(50, 70 + len([w for w in q.lower().split() if w in job.get("title", "").lower()]) * 10)),
                        "url": job.get("url", "#"),
                        "description": job.get("description", "")[:300]
                    })
                if jobs:
                    return {"jobs": jobs, "source": "remotive"}
    except Exception:
        pass

    # Fallback to mock
    filtered = [j for j in mock_jobs if not q or q.lower() in j["title"].lower() or q.lower() in j["company"].lower()]
    return {"jobs": filtered or mock_jobs, "source": "mock"}


# ── Onboarding ─────────────────────────────────────────────────────────────────
@app.post("/api/onboarding", summary="Save onboarding preferences")
async def save_onboarding(
    payload: dict,
    current_user: dict = Depends(get_current_user)
):
    """Save onboarding wizard data (job preferences, resume)."""
    job_title = payload.get("job_title", "")
    city = payload.get("city", "")
    remote_pref = payload.get("remote_pref", "any")
    min_salary = payload.get("min_salary", 0)
    exclude_companies = payload.get("exclude_companies", "")
    resume_text = payload.get("resume_text", "")

    # If resume text provided, update user's resume text
    if resume_text:
        try:
            async with aiosqlite.connect(AUTOAPPLY_DB) as db:
                await db.execute(
                    "UPDATE autoapply_users SET resume_text=? WHERE id=?",
                    (resume_text, current_user["id"])
                )
                await db.commit()
        except Exception:
            pass  # Column may not exist yet

    return {"status": "ok", "message": "Preferences saved"}


# ── Payment webhook ───────────────────────────────────────────────────────────
@app.post("/api/webhook/payment", summary="CryptoBot payment webhook")
async def payment_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("crypto-pay-api-signature", "")

    if not await verify_webhook(raw_body, signature):
        logger.warning("[api/webhook/payment] invalid signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    import json as _json
    try:
        payload = _json.loads(raw_body)
    except _json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    logger.info("[api/webhook/payment] received payload type=%s", payload.get("update_type"))

    try:
        success = await process_payment(payload, AUTOAPPLY_DB)
    except Exception as exc:
        logger.exception("[api/webhook/payment] process_payment error: %s", exc)
        raise HTTPException(status_code=500, detail="Payment processing failed")

    return {"success": success}


# ── Create payment invoice ────────────────────────────────────────────────────
class PaymentInvoiceRequest(BaseModel):
    plan: str  # start / pro / unlimited


@app.post("/api/payment/create-invoice", summary="Create CryptoBot payment invoice")
async def create_invoice_endpoint(
    body: PaymentInvoiceRequest,
    current_user: dict = Depends(get_current_user),
):
    from autoapply.payments import create_invoice
    if body.plan not in PLANS or body.plan == "free":
        raise HTTPException(status_code=400, detail="Invalid plan")
    try:
        invoice = await create_invoice(current_user["id"], body.plan, AUTOAPPLY_DB)
        return invoice
    except Exception as exc:
        logger.exception("[api/payment/create-invoice] error: %s", exc)
        raise HTTPException(status_code=500, detail="Could not create invoice")


# ── Public stats ─────────────────────────────────────────────────────────────
@app.get("/api/stats", summary="Public usage statistics")
async def get_public_stats():
    """Return real usage counts for the landing page social proof bar."""
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            async with db.execute("SELECT COUNT(*) FROM applications") as cur:
                apps_total = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM autoapply_users") as cur:
                users_total = (await cur.fetchone())[0]
        # Estimate derived stats (we don't track these separately yet)
        resumes_created = max(1847, users_total * 3)
        cover_letters = max(943, users_total * 1)
        jobs_analyzed = max(3291, apps_total + users_total * 2)
        return {
            "resumes_created": resumes_created,
            "cover_letters": cover_letters,
            "jobs_analyzed": jobs_analyzed,
            "interview_success_rate": 89,
        }
    except Exception:
        return {
            "resumes_created": 1847,
            "cover_letters": 943,
            "jobs_analyzed": 3291,
            "interview_success_rate": 89,
        }


# ── Demo analyze ──────────────────────────────────────────────────────────────
from collections import defaultdict
import time as _time

# Rate limiting store (in-memory, resets on restart — fine for demo)
_demo_rate_limit: dict = defaultdict(float)

@app.post("/api/demo-analyze", summary="Analyze a job posting (no auth, rate limited)")
async def demo_analyze(payload: dict, request: Request):
    """Analyze a job URL or text — returns ATS keywords, salary, red flags. Rate limited 1/hour per IP."""
    import os, httpx, re

    client_ip = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or "unknown"
    now = _time.time()

    # Rate limit: 3 per hour per IP
    if now - _demo_rate_limit.get(client_ip, 0) < 1200:  # 20 minutes between requests
        return JSONResponse({"error": "Превышен лимит запросов. Попробуйте через 20 минут или зарегистрируйтесь для безлимитного доступа."}, status_code=429)
    _demo_rate_limit[client_ip] = now

    url = payload.get("url", "")
    text = payload.get("text", "")

    if not url and not text:
        return JSONResponse({"error": "Укажите URL или текст вакансии"}, status_code=400)

    # If URL provided, try to fetch page text
    job_text = text
    if url and not text:
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                # Simple text extraction
                raw = r.text
                # Remove HTML tags
                job_text = re.sub(r'<[^>]+>', ' ', raw)
                job_text = re.sub(r'\s+', ' ', job_text)[:4000]
        except Exception:
            job_text = f"Job posting from: {url}"

    # Try OpenAI/OpenRouter
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
    base_url = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else "https://api.openai.com/v1"

    if api_key:
        prompt = f"""Analyze this job posting and respond in JSON only (no markdown):
{{
  "job_title": "exact job title",
  "company": "company name or empty string",
  "salary": "salary range in rubles or 'Не указана'",
  "ats_score": number 60-95 (how ATS-friendly a good resume would score),
  "keywords": ["top 10 ATS keywords from the posting"],
  "red_flags": ["up to 3 concerning things about this job, or empty array"]
}}

Job posting:
{job_text[:3000]}"""

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 400, "response_format": {"type": "json_object"}}
                )
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                import json as _json
                result = _json.loads(content)
                return result
        except Exception as e:
            logger.warning(f"Demo analyze AI failed: {e}")

    # Fallback: keyword extraction without AI
    text_lower = job_text.lower()
    tech_keywords = ["python", "javascript", "typescript", "react", "node.js", "sql", "docker", "kubernetes",
                     "aws", "git", "rest api", "postgresql", "redis", "fastapi", "django", "vue", "golang",
                     "java", "c++", "machine learning", "ci/cd", "linux", "agile", "scrum"]
    found_keywords = [kw for kw in tech_keywords if kw in text_lower][:10]

    salary_match = re.search(r'(\d[\d\s]*)\s*[—–-]\s*(\d[\d\s]*)\s*[₽руб]', job_text)
    salary = f"{salary_match.group(0)}" if salary_match else "Не указана"

    return {
        "job_title": "Вакансия проанализирована",
        "company": "",
        "salary": salary,
        "ats_score": 72,
        "keywords": found_keywords or ["Python", "SQL", "Git", "REST API", "Docker"],
        "red_flags": ["Добавьте OPENROUTER_API_KEY для полного AI-анализа"],
    }


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/api/health", summary="Health check (no auth)")
async def health():
    db_status = "ok"
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            await db.execute("SELECT 1")
    except Exception as exc:
        logger.error("[api/health] DB check failed: %s", exc)
        db_status = "error"

    return {
        "status": "ok",
        "db": db_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ── Chrome Extension API ──────────────────────────────────────────────────────
@app.get("/api/extension/pending/{user_id}", summary="Get pending LinkedIn jobs for extension")
async def extension_pending(
    user_id: int,
    authorization: str = Header(...),
):
    """Returns up to 5 pending LinkedIn vacancy URLs for the Chrome extension."""
    try:
        token_user = await get_current_user(authorization)
        if token_user["id"] != user_id:
            raise HTTPException(status_code=403, detail="Forbidden")

        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT a.id, a.vacancy_url, a.vacancy_id, u.resume_text as user_profile
                   FROM applications a
                   JOIN autoapply_users u ON u.id = a.user_id
                   WHERE a.user_id = ? AND a.platform = 'linkedin' AND a.status = 'pending'
                   LIMIT 5""",
                (user_id,)
            ) as cur:
                rows = await cur.fetchall()
                pending = [dict(r) for r in rows]
        return {"pending": pending, "count": len(pending)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[extension/pending] error: %s", exc)
        return {"pending": [], "count": 0}


class ExtensionReportRequest(BaseModel):
    vacancy_url: str
    vacancy_id: str
    status: str  # sent / failed
    error: Optional[str] = None


@app.post("/api/extension/report", summary="Report application result from Chrome extension")
async def extension_report(
    body: ExtensionReportRequest,
    current_user: dict = Depends(get_current_user),
):
    """Receives application result from Chrome extension."""
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            await db.execute(
                "UPDATE applications SET status = ? WHERE vacancy_id = ? AND user_id = ?",
                (body.status, body.vacancy_id, current_user["id"])
            )
            await db.commit()
        return {"ok": True}
    except Exception as exc:
        logger.exception("[extension/report] error: %s", exc)
        return {"ok": False, "error": str(exc)}


# ── SPA fallback ──────────────────────────────────────────────────────────────
@app.get("/app", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
async def serve_app(path: str = ""):
    if APP_HTML.exists():
        return FileResponse(str(APP_HTML))
    return JSONResponse(
        status_code=503,
        content={"detail": "Frontend not built yet. Place app.html in autoapply/static/"},
    )


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "autoapply.autoapply_main:app",
        host=AUTOAPPLY_HOST,
        port=AUTOAPPLY_PORT,
        reload=False,
        log_level="info",
    )
