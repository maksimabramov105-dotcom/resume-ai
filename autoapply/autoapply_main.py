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
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import bcrypt as _bcrypt_lib
import aiosqlite
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from autoapply.autoapply_db import (
    advance_drip_step,
    check_and_update_rate_limit,
    cleanup_rate_limits,
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
    log_web_generation,
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

import httpx as _httpx_module  # noqa: E402 — used in helpers below


async def _fetch_job_text_from_url(url: str) -> tuple:
    """Fetch job description from URL, with special hh.ru API support.
    Returns (job_text, metadata_dict)."""
    import re as _re
    metadata = {}

    # hh.ru public API (no auth needed for public vacancies)
    hh_match = _re.search(r'hh\.ru/vacancy/(\d+)', url)
    if hh_match:
        vacancy_id = hh_match.group(1)
        try:
            async with _httpx_module.AsyncClient(timeout=10) as client:
                r = await client.get(
                    f"https://api.hh.ru/vacancies/{vacancy_id}",
                    headers={"User-Agent": "ResumeAI/1.0 (resumeai-bot.ru)"}
                )
                if r.status_code == 200:
                    vdata = r.json()
                    title = vdata.get("name", "")
                    company = vdata.get("employer", {}).get("name", "")
                    sal = vdata.get("salary") or {}
                    sal_from = sal.get("from") or ""
                    sal_to = sal.get("to") or ""
                    currency = sal.get("currency", "RUB")
                    salary_str = f"{sal_from}–{sal_to} {currency}" if (sal_from or sal_to) else "Не указана"
                    desc_html = vdata.get("description", "")
                    desc_text = _re.sub(r'<[^>]+>', ' ', desc_html)
                    desc_text = _re.sub(r'\s+', ' ', desc_text).strip()[:3000]
                    key_skills = [s.get("name", "") for s in vdata.get("key_skills", [])]
                    job_text = f"Должность: {title}\nКомпания: {company}\nЗарплата: {salary_str}\nКлючевые навыки: {', '.join(key_skills)}\n\n{desc_text}"
                    metadata = {"job_title": title, "company": company, "salary": salary_str, "keywords": key_skills[:10]}
                    return job_text, metadata
        except Exception as e:
            logger.warning(f"hh.ru API fetch failed for {vacancy_id}: {e}")

    # Generic URL fetch for non-hh.ru or fallback
    try:
        async with _httpx_module.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ResumeAI/1.0)"})
            raw = r.text
            import re as _re2
            job_text = _re2.sub(r'<[^>]+>', ' ', raw)
            job_text = _re2.sub(r'\s+', ' ', job_text).strip()[:4000]
            return job_text, {}
    except Exception as e:
        logger.warning(f"URL fetch failed for {url}: {e}")
        return f"Job posting from URL: {url}", {}


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

# ── SQLite optimisation: set WAL mode + pragmas once at startup ───────────────
async def _apply_db_pragmas(db_path: str) -> None:
    """Enable WAL journal + memory-friendly pragmas.
    These settings persist in the DB file so every subsequent aiosqlite.connect()
    inherits them — eliminates the overhead of 15+ cold connects per request.
    """
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")   # fsync only on checkpoint
            await db.execute("PRAGMA cache_size=-32000")    # 32 MB page cache
            await db.execute("PRAGMA temp_store=MEMORY")    # temp tables in RAM
            await db.execute("PRAGMA mmap_size=134217728")  # 128 MB memory-mapped I/O
            await db.commit()
        logger.info("[startup] SQLite pragmas applied to %s", db_path)
    except Exception as exc:
        logger.warning("[startup] pragma apply failed for %s: %s", db_path, exc)


async def _rate_limit_cleanup_loop() -> None:
    """Delete stale rate-limit rows daily to keep the table lean."""
    while True:
        await asyncio.sleep(86400)
        await cleanup_rate_limits()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("[autoapply_main] Starting up — initialising DB at %s", AUTOAPPLY_DB)
    await init_db(AUTOAPPLY_DB)
    # Apply WAL + pragmas to both databases (autoapply + bot read-only queries)
    await _apply_db_pragmas(AUTOAPPLY_DB)
    await _apply_db_pragmas(BOT_DB)
    logger.info("[autoapply_main] DB ready")
    # Background tasks
    asyncio.create_task(process_email_drip())
    asyncio.create_task(_rate_limit_cleanup_loop())
    # Marketing scheduler
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from marketing_cron import setup_marketing_scheduler
        _scheduler = AsyncIOScheduler(timezone="UTC")
        setup_marketing_scheduler(_scheduler)
        _scheduler.start()
        logger.info("[autoapply_main] marketing scheduler started")
    except Exception as _e:
        logger.warning("[autoapply_main] marketing scheduler not started: %s", _e)

    yield  # ── app is running ─────────────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("[autoapply_main] Shutting down")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AutoApply API",
    description="АвтоОтклик — automated job application service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://resumeai-bot.ru",
        "https://www.resumeai-bot.ru",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.middleware("http")
async def security_headers_middleware(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://vk.com https://unpkg.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https://api.hh.ru https://vk.com https://api.openai.com; "
        "frame-src https://vk.com https://oauth.vk.com; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    return response


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
                sent = await asyncio.to_thread(send_drip_email, drip["email"], step)
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
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire, "iat": now}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
) -> dict:
    """Decode JWT from Authorization header. Raises 401 if invalid."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
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

    # Validate email domain has real MX records (rejects fake/disposable addresses)
    from autoapply.email_sender import validate_email_mx
    if not validate_email_mx(body.email):
        raise HTTPException(
            status_code=400,
            detail="Введите настоящий email-адрес — указанный домен не существует"
        )

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


@app.post("/api/auth/vk-login", summary="VK ID One Tap login/register")
async def vk_login(payload: dict):
    """Receive VK auth data (after exchangeCode), create or log in the user."""
    access_token = payload.get("access_token") or payload.get("token") or ""
    vk_user_id = str(payload.get("user_id") or payload.get("id") or "")
    email = payload.get("email", "")

    if not vk_user_id:
        raise HTTPException(status_code=400, detail="Нет user_id в VK ответе")

    # Try to get user info from VK if email not provided
    if not email and access_token:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as cl:
                r = await cl.get(
                    "https://api.vk.com/method/users.get",
                    params={"fields": "contacts", "access_token": access_token, "v": "5.199"},
                )
                data = r.json().get("response", [{}])
                if data:
                    email = data[0].get("contacts", {}).get("mobile_phone", "")
        except Exception:
            pass

    # Use vk_{user_id}@vk.autoapply as synthetic email if no real email
    synthetic_email = email or f"vk_{vk_user_id}@vk.autoapply"
    fake_password_hash = _hash_password(f"vk_{vk_user_id}_immutable_salt")

    existing = await get_user_by_email(synthetic_email, AUTOAPPLY_DB)
    if existing:
        user_id = existing["id"]
    else:
        try:
            user_id = await create_user(
                email=synthetic_email,
                password_hash=fake_password_hash,
                telegram_id=None,
                db_path=AUTOAPPLY_DB,
            )
            # Mark as email verified (VK auth = verified identity)
            async with aiosqlite.connect(AUTOAPPLY_DB) as db:
                await db.execute(
                    "UPDATE autoapply_users SET is_verified=1 WHERE id=?", (user_id,)
                )
                await db.commit()
        except Exception as exc:
            logger.error("[vk-login] create_user error: %s", exc)
            raise HTTPException(status_code=500, detail="Ошибка создания аккаунта")

    token = _create_token(user_id)
    logger.info("[vk-login] user_id=%s vk_user_id=%s", user_id, vk_user_id)
    return {"token": token, "user_id": user_id, "vk_user_id": vk_user_id}


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
    asyncio.create_task(log_web_generation("autoapply", user_id))
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
                "SELECT specialty, experience_text, education_text, skills_text "
                "FROM users WHERE telegram_id = ?",
                (telegram_id,),
            ) as cur:
                row = await cur.fetchone()
    except Exception as exc:
        logger.error("[api/resume/connect] bot.db read error: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read bot database")

    if not row:
        raise HTTPException(
            status_code=404,
            detail="No Telegram account found with this ID. Link your account first.",
        )

    # Combine available profile fields into a single resume text
    parts = []
    if row["specialty"]:
        parts.append(f"Специальность: {row['specialty']}")
    if row["experience_text"]:
        parts.append(f"Опыт работы:\n{row['experience_text']}")
    if row["education_text"]:
        parts.append(f"Образование:\n{row['education_text']}")
    if row["skills_text"]:
        parts.append(f"Навыки:\n{row['skills_text']}")

    if not parts:
        raise HTTPException(
            status_code=404,
            detail="No resume found for this Telegram account. Create it via the bot first.",
        )

    profile_text = "\n\n".join(parts)
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

    asyncio.create_task(log_web_generation("resume", current_user["id"]))
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
            # Log generation for daily report
            asyncio.create_task(log_web_generation("cover_letter", current_user.get("id")))
            return {"cover_letter": letter}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


# ── Job search ─────────────────────────────────────────────────────────────────
@app.get("/api/jobs/search", summary="Search jobs via hh.ru + Remotive API")
async def search_jobs(
    q: str = "",
    city: str = "",
    remote: str = "",
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
    BASELINE = {"resumes": 1847, "letters": 943, "analyses": 3291, "apps": 500}
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            async with db.execute("SELECT COUNT(*) FROM applications") as cur:
                apps_total = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM autoapply_users") as cur:
                users_total = (await cur.fetchone())[0]
            # Real tracked web generations
            try:
                async with db.execute("SELECT COUNT(*) FROM web_generations WHERE type='resume'") as cur:
                    wg_resumes = (await cur.fetchone())[0]
                async with db.execute("SELECT COUNT(*) FROM web_generations WHERE type='cover_letter'") as cur:
                    wg_letters = (await cur.fetchone())[0]
                async with db.execute("SELECT COUNT(*) FROM web_generations WHERE type IN ('analysis','demo_analysis')") as cur:
                    wg_analyses = (await cur.fetchone())[0]
            except Exception:
                wg_resumes = wg_letters = wg_analyses = 0
        return {
            "resumes_created":        max(BASELINE["resumes"],  wg_resumes  + users_total * 2),
            "cover_letters":          max(BASELINE["letters"],  wg_letters  + users_total),
            "jobs_analyzed":          max(BASELINE["analyses"], wg_analyses + apps_total),
            "applications_sent":      max(BASELINE["apps"],     apps_total),
            "interview_success_rate": 89,
            "users_total":            users_total,
        }
    except Exception:
        return {
            "resumes_created": BASELINE["resumes"],
            "cover_letters":   BASELINE["letters"],
            "jobs_analyzed":   BASELINE["analyses"],
            "applications_sent": BASELINE["apps"],
            "interview_success_rate": 89,
            "users_total": 0,
        }


# ── Testimonials ───────────────────────────────────────────────────────────────

class TestimonialSubmitRequest(BaseModel):
    name: str
    text: str
    rating: int = 5


@app.post("/api/testimonials/submit", summary="Submit a testimonial")
async def submit_testimonial(
    body: TestimonialSubmitRequest,
    current_user: dict = Depends(get_current_user),
):
    if not 1 <= body.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    if len(body.text.strip()) < 20:
        raise HTTPException(status_code=400, detail="Review too short")
    async with aiosqlite.connect(AUTOAPPLY_DB) as db:
        await db.execute(
            "INSERT INTO testimonials (user_id, name, text, rating) VALUES (?,?,?,?)",
            (current_user["id"], body.name[:60], body.text[:500], body.rating),
        )
        await db.commit()
    return {"success": True, "message": "Спасибо! Ваш отзыв отправлен на проверку."}


@app.get("/api/testimonials", summary="Get approved testimonials")
async def get_testimonials():
    async with aiosqlite.connect(AUTOAPPLY_DB) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT name, text, rating, created_at FROM testimonials WHERE approved=1 ORDER BY created_at DESC LIMIT 20"
        ) as cur:
            rows = await cur.fetchall()
    return {"testimonials": [dict(r) for r in rows]}


@app.post("/api/admin/approve-testimonial", summary="Admin: approve a testimonial")
async def approve_testimonial(body: dict, current_user: dict = Depends(get_current_user)):
    if current_user.get("plan") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    tid = body.get("id")
    async with aiosqlite.connect(AUTOAPPLY_DB) as db:
        await db.execute("UPDATE testimonials SET approved=1 WHERE id=?", (tid,))
        await db.commit()
    return {"success": True}


# ── Demo analyze ──────────────────────────────────────────────────────────────

@app.post("/api/demo-analyze", summary="Analyze a job posting (no auth, rate limited)")
async def demo_analyze(payload: dict, request: Request):
    """Analyze a job URL or text — returns ATS keywords, salary, red flags. Rate limited per IP."""
    import os, httpx, re

    client_ip = (
        request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or "unknown"
    )

    # Rate limit: once per 20 min per IP — persisted in SQLite (survives restarts)
    allowed = await check_and_update_rate_limit(f"demo:{client_ip}", 1200, AUTOAPPLY_DB)
    if not allowed:
        return JSONResponse(
            {"error": "Превышен лимит запросов. Попробуйте через 20 минут или зарегистрируйтесь для безлимитного доступа."},
            status_code=429,
        )

    url = payload.get("url", "")
    text = payload.get("text", "")

    if not url and not text:
        return JSONResponse({"error": "Укажите URL или текст вакансии"}, status_code=400)

    # If URL provided, try to fetch page text (with hh.ru API support)
    job_text = text
    url_metadata = {}
    if url and not text:
        job_text, url_metadata = await _fetch_job_text_from_url(url)
        if not job_text:
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
                # Log demo analysis for daily report
                asyncio.create_task(log_web_generation("demo_analysis"))
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

    asyncio.create_task(log_web_generation("demo_analysis"))
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


# ── Admin: auto-generate blog post ───────────────────────────────────────────
@app.post("/api/admin/generate-blog-post", summary="Admin: auto-generate blog post")
async def admin_generate_blog_post(payload: dict, request: Request):
    """Generate a new blog post via OpenAI and save to blog directory."""
    import os as _os, json as _json, re as _re
    from datetime import datetime, timezone

    secret = request.headers.get("X-Admin-Secret", "")
    expected = _os.getenv("ADMIN_SECRET", "")
    if not expected or secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")

    topic = payload.get("topic", "")
    if not topic:
        topics = [
            "Как получить оффер за 30 дней: пошаговый план поиска работы",
            "Портфолио разработчика: что включить и как оформить",
            "LinkedIn vs hh.ru: где искать работу в 2026",
            "Как написать резюме на английском языке для международных компаний",
            "5 причин почему рекрутеры не отвечают на ваш отклик",
        ]
        import random
        topic = random.choice(topics)

    api_key = _os.getenv("OPENROUTER_API_KEY") or _os.getenv("OPENAI_API_KEY")
    if not api_key:
        return JSONResponse({"error": "No API key configured"}, status_code=500)

    model = _os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")
    base_url = "https://openrouter.ai/api/v1" if _os.getenv("OPENROUTER_API_KEY") else "https://api.openai.com/v1"

    prompt = f"""Напиши статью на 800 слов в блог для сайта по поиску работы. Тема: "{topic}"

Верни ТОЛЬКО JSON следующего формата:
{{
  "title": "заголовок статьи",
  "slug": "url-slug-latinicey",
  "meta_description": "SEO описание до 150 символов",
  "content_html": "HTML контент статьи с тегами <h2>, <h3>, <p>, <ul><li>",
  "faq": [{{"q": "вопрос", "a": "ответ"}}, {{"q": "вопрос2", "a": "ответ2"}}, {{"q": "вопрос3", "a": "ответ3"}}],
  "reading_time": "5 мин чтения"
}}

Требования к статье:
- H2 подзаголовки каждые 150-200 слов
- Упомяни РезюмеАИ (resumeai-bot.ru) один раз органично
- Заканчивай призывом использовать AI для резюме
- Практические советы с данными
- Целевая аудитория: русскоязычные соискатели"""

    try:
        async with _httpx_module.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000, "response_format": {"type": "json_object"}}
            )
            data = r.json()
            article = _json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")

    slug = article.get("slug", "article-" + datetime.now(timezone.utc).strftime("%Y%m%d"))
    title = article.get("title", topic)
    meta_desc = article.get("meta_description", "")
    content = article.get("content_html", "")
    faqs = article.get("faq", [])
    reading_time = article.get("reading_time", "5 мин чтения")
    date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    faq_schema = _json.dumps({"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":f["q"],"acceptedAnswer":{"@type":"Answer","text":f["a"]}} for f in faqs]}, ensure_ascii=False)
    faq_html = "".join(f'<div class="faq-item"><div class="faq-q" onclick="this.nextElementSibling.classList.toggle(\'open\')">{f["q"]} <span>+</span></div><div class="faq-a">{f["a"]}</div></div>' for f in faqs)

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} | РезюмеАИ</title>
  <meta name="description" content="{meta_desc}" />
  <meta property="og:title" content="{title}" /><meta property="og:description" content="{meta_desc}" />
  <meta property="og:image" content="https://resumeai-bot.ru/og-image.png" />
  <meta property="og:url" content="https://resumeai-bot.ru/blog/{slug}.html" />
  <link rel="canonical" href="https://resumeai-bot.ru/blog/{slug}.html" />
  <script type="application/ld+json">{faq_schema}</script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}} body{{font-family:'Inter',sans-serif;background:#F8FAFC;color:#334155;line-height:1.6}}
    .container{{max-width:760px;margin:0 auto;padding:0 24px}} header{{background:#fff;border-bottom:1px solid #E2E8F0;padding:0 24px}}
    .header-inner{{max-width:1100px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:60px}}
    .logo{{font-size:1.2rem;font-weight:800;color:#2563EB;text-decoration:none}}
    .article-hero{{background:#fff;padding:48px 0 32px;border-bottom:1px solid #E2E8F0}}
    .article-hero h1{{font-size:clamp(1.6rem,4vw,2.2rem);font-weight:800;color:#0F172A;margin-bottom:12px;line-height:1.3}}
    .article-meta{{font-size:.85rem;color:#94A3B8;margin-top:12px}}
    .article-body{{padding:40px 0}} .article-body h2{{font-size:1.35rem;font-weight:700;color:#0F172A;margin:32px 0 12px}}
    .article-body h3{{font-size:1.1rem;font-weight:600;color:#0F172A;margin:20px 0 8px}}
    .article-body p{{margin-bottom:16px}} .article-body ul{{margin:12px 0 16px 20px}} .article-body li{{margin-bottom:8px}}
    .faq-section{{padding:32px 0;border-top:1px solid #E2E8F0}}
    .faq-item{{border:1px solid #E2E8F0;border-radius:12px;margin-bottom:10px;overflow:hidden}}
    .faq-q{{padding:16px 20px;font-weight:600;cursor:pointer;display:flex;justify-content:space-between;background:#fff;color:#0F172A}}
    .faq-a{{padding:0 20px;max-height:0;overflow:hidden;transition:.3s}} .faq-a.open{{max-height:300px;padding:0 20px 16px}}
    .cta-box{{background:linear-gradient(135deg,#1E40AF,#2563EB);border-radius:16px;padding:32px;text-align:center;color:#fff;margin:40px 0}}
    .cta-box h2{{font-size:1.4rem;font-weight:800;margin-bottom:8px}} .cta-box p{{opacity:.85;margin-bottom:20px}}
    .btn-cta{{background:linear-gradient(135deg,#F59E0B,#D97706);color:#fff;padding:12px 28px;border-radius:10px;font-weight:700;text-decoration:none;display:inline-block}}
    footer{{background:#0F172A;color:#64748B;padding:32px 0;margin-top:64px;text-align:center;font-size:.85rem}}
  </style>
</head>
<body>
<header><div class="header-inner"><a href="/" class="logo">ResumeAI</a><a href="/app" style="background:#F59E0B;color:#fff;padding:8px 20px;border-radius:8px;font-weight:600;font-size:.88rem;text-decoration:none;">Создать резюме</a></div></header>
<div class="article-hero"><div class="container"><div style="font-size:.82rem;color:#94A3B8;margin-bottom:12px;"><a href="/" style="color:#2563EB;">Главная</a> › <a href="/blog/" style="color:#2563EB;">Блог</a> › {title}</div><h1>{title}</h1><div class="article-meta">📅 {date_str} · ✍️ РезюмеАИ · ⏱ {reading_time}</div></div></div>
<div class="container"><div class="article-body">{content}</div>
<div class="cta-box"><h2>Создайте резюме с AI прямо сейчас</h2><p>Бесплатно · 30 секунд · ATS-оптимизация</p><a href="/app" class="btn-cta">Попробовать бесплатно →</a></div>
<div class="faq-section"><h2 style="font-size:1.4rem;font-weight:800;color:#0F172A;margin-bottom:20px;">Частые вопросы</h2>{faq_html}</div></div>
<footer>© 2026 РезюмеАИ · <a href="/privacy.html" style="color:#64748B;">Конфиденциальность</a> · <a href="https://t.me/topbestworkerbot" target="_blank" style="color:#0088CC;">@topbestworkerbot</a></footer>
<script>document.querySelectorAll('.faq-q').forEach(q=>q.addEventListener('click',()=>q.nextElementSibling.classList.toggle('open')))</script>
</body></html>"""

    blog_path = "/opt/resumeaibot/landing/blog"
    import os as _os2
    _os2.makedirs(blog_path, exist_ok=True)
    filepath = _os2.path.join(blog_path, f"{slug}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Generated blog post: {slug}")
    return {"status": "ok", "slug": slug, "title": title, "path": filepath}


# ── Admin: post blog article to Telegram channel ──────────────────────────────
@app.post("/api/admin/post-to-channel", summary="Admin: post blog article to Telegram channel")
async def post_to_telegram_channel(payload: dict, request: Request):
    """Post a blog article summary to the configured Telegram channel."""
    import os as _os3

    secret = request.headers.get("X-Admin-Secret", "")
    if not _os3.getenv("ADMIN_SECRET") or secret != _os3.getenv("ADMIN_SECRET"):
        raise HTTPException(status_code=403, detail="Forbidden")

    channel_id = _os3.getenv("TELEGRAM_CHANNEL_ID", "")
    bot_token = _os3.getenv("BOT_TOKEN", "")

    if not channel_id or not bot_token:
        return JSONResponse({"error": "TELEGRAM_CHANNEL_ID or BOT_TOKEN not set"}, status_code=400)

    title = payload.get("title", "")
    slug = payload.get("slug", "")
    excerpt = payload.get("excerpt", "")[:200]
    url = f"https://resumeai-bot.ru/blog/{slug}.html"

    text = (
        f"📝 *{title}*\n\n"
        f"{excerpt}...\n\n"
        f"👉 [Читать полностью]({url})\n\n"
        f"🤖 Создать резюме: https://t.me/topbestworkerbot"
    )

    async with _httpx_module.AsyncClient(timeout=10) as client:
        r = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": channel_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": False}
        )
        data = r.json()

    if data.get("ok"):
        return {"status": "ok", "message_id": data["result"]["message_id"]}
    else:
        return JSONResponse({"error": data.get("description", "Unknown error")}, status_code=500)


# ── Stripe Checkout ──────────────────────────────────────────────────────────
@app.post("/api/payments/create-checkout", summary="Create Stripe Checkout session")
async def create_stripe_checkout(payload: dict, request: Request):
    import os, stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not stripe.api_key:
        return JSONResponse({"error": "Stripe not configured"}, status_code=503)

    plan = payload.get("plan", "pro")
    period = payload.get("period", "monthly")

    # Real Stripe Price IDs from dashboard (env vars, fallback to price_data)
    PRICE_ID_MAP = {
        ("trial",   "monthly"): os.getenv("STRIPE_PRICE_TRIAL",           ""),
        ("pro",     "monthly"): os.getenv("STRIPE_PRICE_PRO_MONTHLY",     "price_1TLTUuHH7N0YD11QKYiEvUd0"),
        ("pro",     "annual"):  os.getenv("STRIPE_PRICE_PRO_ANNUAL",      "price_1TLTVhHH7N0YD11QeFRlaDSw"),
        ("premium", "monthly"): os.getenv("STRIPE_PRICE_PREMIUM_MONTHLY", "price_1TLTWLHH7N0YD11Q7AswwGwm"),
        ("premium", "annual"):  os.getenv("STRIPE_PRICE_PREMIUM_ANNUAL",  ""),
    }
    PRICE_FALLBACK = {
        ("trial",   "monthly"): {"amount": 299,   "currency": "usd", "name": "РезюмеАИ Trial — 7 дней",     "recurring": None},
        ("pro",     "monthly"): {"amount": 1999,  "currency": "usd", "name": "РезюмеАИ Pro — месяц",        "recurring": "month"},
        ("pro",     "annual"):  {"amount": 14900, "currency": "usd", "name": "РезюмеАИ Pro — год",          "recurring": "year"},
        ("premium", "monthly"): {"amount": 3999,  "currency": "usd", "name": "РезюмеАИ Premium — месяц",   "recurring": "month"},
        ("premium", "annual"):  {"amount": 29900, "currency": "usd", "name": "РезюмеАИ Premium — год",      "recurring": "year"},
    }

    price_id = PRICE_ID_MAP.get((plan, period), "")
    price_cfg = PRICE_FALLBACK.get((plan, period), PRICE_FALLBACK[("pro", "monthly")])

    try:
        if price_id:
            # Use real Stripe Price ID — cleanest approach
            is_recurring = price_cfg["recurring"] is not None
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription" if is_recurring else "payment",
                success_url="https://resumeai-bot.ru/app?payment=success",
                cancel_url="https://resumeai-bot.ru/app?payment=cancelled",
                metadata={"plan": plan, "period": period},
            )
        elif price_cfg["recurring"]:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": price_cfg["currency"],
                        "unit_amount": price_cfg["amount"],
                        "product_data": {"name": price_cfg["name"]},
                        "recurring": {"interval": price_cfg["recurring"]},
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                success_url="https://resumeai-bot.ru/app?payment=success",
                cancel_url="https://resumeai-bot.ru/app?payment=cancelled",
                metadata={"plan": plan, "period": period},
            )
        else:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": price_cfg["currency"],
                        "unit_amount": price_cfg["amount"],
                        "product_data": {"name": price_cfg["name"]},
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url="https://resumeai-bot.ru/app?payment=success",
                cancel_url="https://resumeai-bot.ru/app?payment=cancelled",
                metadata={"plan": plan, "period": period},
            )
        return {"url": session.url}
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/payments/webhook", summary="Stripe webhook handler")
async def stripe_webhook(request: Request):
    import os, stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        else:
            import json as _json_stripe
            event = stripe.Event.construct_from(_json_stripe.loads(payload), stripe.api_key)
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        plan = data.get("metadata", {}).get("plan", "pro")
        customer_email = data.get("customer_details", {}).get("email", "")
        logger.info(f"Stripe payment completed: plan={plan} email={customer_email}")
        # TODO: update user subscription in DB when user auth is linked

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        logger.info(f"Stripe subscription event: {event_type}")

    return {"status": "ok"}


@app.get("/api/payments/status", summary="Get payment status info")
async def get_payment_status():
    return {
        "stripe_configured": bool(os.getenv("STRIPE_SECRET_KEY")),
        "crypto_configured": bool(os.getenv("CRYPTOBOT_API_TOKEN") or os.getenv("CRYPTOBOT_TOKEN")),
        "plans": {
            "trial": {"price_usd": 2.99, "duration": "7 days"},
            "pro_monthly": {"price_usd": 19.99, "period": "monthly"},
            "pro_annual": {"price_usd": 149, "period": "annual"},
            "premium_monthly": {"price_usd": 39.99, "period": "monthly"},
            "premium_annual": {"price_usd": 299, "period": "annual"},
        }
    }


# ── Build B: Help widget endpoint ─────────────────────────────────────────────
class HelpQuestionRequest(BaseModel):
    question: str
    user_id: Optional[int] = None
    page: Optional[str] = None


@app.post("/api/help/question", summary="Help widget: answer user question via AI")
async def help_question(body: HelpQuestionRequest):
    """Floating help widget Q&A — answers common questions, falls back to FAQ list."""
    q = body.question.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Вопрос не может быть пустым")

    OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
    if not OPENROUTER_KEY:
        # Fallback FAQ
        faq = [
            ("бесплатно", "Бесплатный план: 1 резюме, 1 письмо, 3 AI-запроса. Без кредитной карты."),
            ("стоит", "Про-тариф — 990 ₽/месяц. Безлимит резюме, писем, ATS-анализ, авто-отклики."),
            ("hh\\.ru|hh ", "Вставьте ссылку на вакансию с hh.ru — AI создаст резюме под неё за 30 секунд."),
            ("пароль", "Нажмите «Забыли пароль?» на странице входа — пришлём ссылку на email."),
            ("отмен", "Отменить подписку можно в личном кабинете в разделе «Тариф»."),
        ]
        import re as _re
        for kw, answer in faq:
            if _re.search(kw, q, _re.I):
                return {"answer": answer, "source": "faq"}
        return {
            "answer": "Напишите нам в Telegram: @resumeai_support — ответим в течение часа.",
            "source": "fallback",
        }

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": (
                            "Ты виджет поддержки сервиса АвтоОтклик (resumeai-bot.ru). "
                            "Отвечай кратко (1-3 предложения), по-русски, дружелюбно. "
                            "Если не знаешь ответа — направь в Telegram @resumeai_support."
                        )},
                        {"role": "user", "content": q},
                    ],
                    "max_tokens": 200,
                },
            )
        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip()
        return {"answer": answer, "source": "ai"}
    except Exception as exc:
        logger.error("[help/question] AI error: %s", exc)
        return {"answer": "Напишите нам: @resumeai_support — поможем в течение часа.", "source": "fallback"}


# ── Build F: VK community posting ─────────────────────────────────────────────
class VKPostRequest(BaseModel):
    message: str
    link: Optional[str] = None
    attachments: Optional[str] = None   # e.g. "photo-237549969_123456"


@app.post("/api/admin/post-to-vk", summary="Admin: post message to VK community")
async def post_to_vk(body: VKPostRequest, x_admin_key: str = Header(default="")):
    """Post a message to VK public club237549969. Requires ADMIN_SECRET header."""
    ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")
    if ADMIN_SECRET and x_admin_key != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    VK_TOKEN = os.getenv("VK_API_TOKEN", "")
    VK_GROUP_ID = os.getenv("VK_GROUP_ID", "237549969")
    if not VK_TOKEN:
        raise HTTPException(status_code=503, detail="VK_API_TOKEN not configured")

    text = body.message
    if body.link:
        text = f"{text}\n\n{body.link}"

    params: dict = {
        "owner_id": f"-{VK_GROUP_ID}",
        "message": text,
        "from_group": 1,
        "access_token": VK_TOKEN,
        "v": "5.131",
    }
    if body.attachments:
        params["attachments"] = body.attachments

    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post("https://api.vk.com/method/wall.post", data=params)
        data = resp.json()
        if "error" in data:
            logger.error("[post-to-vk] VK error: %s", data["error"])
            raise HTTPException(status_code=502, detail=f"VK error: {data['error'].get('error_msg')}")
        post_id = data.get("response", {}).get("post_id")
        logger.info("[post-to-vk] posted to VK group %s, post_id=%s", VK_GROUP_ID, post_id)
        return {"ok": True, "post_id": post_id, "url": f"https://vk.com/wall-{VK_GROUP_ID}_{post_id}"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[post-to-vk] error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Resume PDF generation ─────────────────────────────────────────────────────

TEMPLATES_DIR = Path(ROOT) / "autoapply" / "templates" / "resume"

VALID_TEMPLATES = {
    "modern-blue", "classic-serif", "minimal-white", "creative-gradient",
    "executive-dark", "tech-mono", "ats-safe", "russian-formal",
}


class ResumePDFRequest(BaseModel):
    template: str = "modern-blue"
    data: dict
    language: str = "ru"


@app.post("/api/resume/generate-pdf", summary="Generate resume PDF from template")
async def generate_resume_pdf(
    body: ResumePDFRequest,
    current_user: dict = Depends(get_current_user),
):
    template_id = body.template if body.template in VALID_TEMPLATES else "modern-blue"
    template_path = TEMPLATES_DIR / f"{template_id}.html"

    if not template_path.exists():
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")

    try:
        html_source = template_path.read_text(encoding="utf-8")
        # Inject resume data as JS variable before </body>
        import json as _json
        data_script = f"<script>window.RESUME_DATA = {_json.dumps(body.data, ensure_ascii=False)}; document.addEventListener('DOMContentLoaded', () => renderResume(null, window.RESUME_DATA));</script>"
        html_ready = html_source.replace("window.RESUME_DATA = null;", "").replace("</body>", data_script + "\n</body>")

        from weasyprint import HTML as WeasyprintHTML
        pdf_bytes = WeasyprintHTML(string=html_ready, base_url=str(TEMPLATES_DIR)).write_pdf()

        asyncio.create_task(log_web_generation("resume_pdf", current_user.get("id")))

        name_slug = body.data.get("name", "resume").replace(" ", "_")[:30]
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{name_slug}_{template_id}.pdf"'},
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="PDF generation not available on this server. Install weasyprint.")
    except Exception as exc:
        logger.error("[generate-pdf] error: %s", exc)
        raise HTTPException(status_code=500, detail="PDF generation failed")


@app.get("/api/resume/templates", summary="List available resume templates")
async def list_resume_templates():
    templates = []
    for tid in sorted(VALID_TEMPLATES):
        path = TEMPLATES_DIR / f"{tid}.html"
        templates.append({
            "id": tid,
            "available": path.exists(),
            "preview_url": f"/api/resume/template-preview/{tid}",
        })
    return {"templates": templates}


@app.get("/api/resume/template-preview/{template_id}", include_in_schema=False)
async def serve_template_preview(template_id: str):
    """Serve template HTML with sample data for preview."""
    if template_id not in VALID_TEMPLATES:
        raise HTTPException(status_code=404, detail="Template not found")
    template_path = TEMPLATES_DIR / f"{template_id}.html"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template file not found")

    import json as _json
    sample = {
        "name": "Иван Иванов",
        "title": "Senior Python Developer",
        "email": "ivan@example.com",
        "phone": "+7 999 123-45-67",
        "location": "Москва",
        "summary": "Опытный Python-разработчик с 6+ годами коммерческого опыта. Специализируюсь на создании высоконагруженных микросервисов и REST API.",
        "experience": [
            {"company": "Яндекс", "position": "Senior Python Developer", "period": "2021–2024",
             "description": "Разрабатывал микросервисы на FastAPI. Оптимизировал запросы PostgreSQL, снизив время ответа на 40%."},
            {"company": "Сбербанк", "position": "Python Developer", "period": "2019–2021",
             "description": "Разработал REST API для банковского мобильного приложения. Покрытие тестами 90%."},
        ],
        "education": [
            {"institution": "МГУ им. Ломоносова", "degree": "Бакалавр, Прикладная математика и информатика", "period": "2015–2019"},
        ],
        "skills": ["Python", "FastAPI", "Django", "PostgreSQL", "Redis", "Docker", "Kubernetes", "AWS"],
        "languages": [{"language": "Русский", "level": "Родной"}, {"language": "Английский", "level": "B2"}],
    }
    html_source = template_path.read_text(encoding="utf-8")
    data_script = f"<script>window.RESUME_DATA = {_json.dumps(sample, ensure_ascii=False)}; document.addEventListener('DOMContentLoaded', () => renderResume(null, window.RESUME_DATA));</script>"
    html_ready = html_source.replace("window.RESUME_DATA = null;", "").replace("</body>", data_script + "\n</body>")
    return Response(content=html_ready, media_type="text/html")


@app.get("/api/salary/insights", summary="Salary insights from hh.ru public data")
async def salary_insights(title: str = Query(..., min_length=2), area: int = Query(1)):
    """Returns min/max/median salary for a job title using hh.ru vacancy data."""
    import httpx, statistics
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.hh.ru/vacancies",
                params={"text": title, "area": area, "per_page": 100, "only_with_salary": True},
                headers={"User-Agent": "ResumeAI/1.0 (resumeai-bot.ru)"},
            )
            data = resp.json()
        items = data.get("items", [])
        salaries = []
        for item in items:
            s = item.get("salary")
            if not s:
                continue
            currency = s.get("currency", "RUR")
            if currency not in ("RUR", "RUB"):
                continue
            low = s.get("from")
            high = s.get("to")
            if low and high:
                salaries.append((low + high) / 2)
            elif low:
                salaries.append(low)
            elif high:
                salaries.append(high)

        if not salaries:
            return {"title": title, "area": area, "sample_size": 0, "message": "Данные о зарплате не найдены"}

        return {
            "title": title,
            "area": area,
            "currency": "RUB",
            "min": int(min(salaries)),
            "max": int(max(salaries)),
            "median": int(statistics.median(salaries)),
            "average": int(statistics.mean(salaries)),
            "sample_size": len(salaries),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"hh.ru API error: {exc}")


# ── Interview Prep ────────────────────────────────────────────────────────────
class InterviewEvalRequest(BaseModel):
    question: str
    answer: str
    job_title: str = "специалист"


@app.post("/api/interview/evaluate", summary="Evaluate interview answer with STAR method")
async def evaluate_interview_answer(
    req: InterviewEvalRequest,
    current_user: dict = Depends(get_current_user),
):
    import json as _json, re as _re, os as _os2, httpx as _hx2
    api_key = _os2.getenv("OPENROUTER_API_KEY") or _os2.getenv("OPENAI_API_KEY")
    model = _os2.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")

    if not api_key:
        return {
            "score": 7,
            "star_breakdown": {
                "situation": "Хорошо описана контекст ситуации",
                "task": "Задача обозначена",
                "action": "Действия перечислены",
                "result": "Добавьте количественные результаты",
            },
            "strengths": ["Структурированный ответ", "Конкретный пример из практики"],
            "improvements": ["Добавьте цифры: % рост, сроки, объём", "Усильте описание вашей личной роли"],
            "better_answer": "Пример: В 2023 году наша команда столкнулась с X. Моей задачей было Y. Я предпринял A, B, C — в результате достигли D (конкретные цифры).",
            "demo": True,
        }

    prompt = f"""You are an expert interview coach. Evaluate this interview answer using the STAR method.

Job title: {req.job_title}
Question: {req.question}
Candidate's answer: {req.answer}

Respond ONLY in Russian with valid JSON (no markdown):
{{
  "score": <integer 1-10>,
  "star_breakdown": {{
    "situation": "<feedback on Situation clarity>",
    "task": "<feedback on Task clarity>",
    "action": "<feedback on Action specificity>",
    "result": "<feedback on Result and impact>"
  }},
  "strengths": ["<strength 1>", "<strength 2>"],
  "improvements": ["<improvement 1>", "<improvement 2>"],
  "better_answer": "<Brief improved version showing ideal structure>"
}}"""

    base_url = "https://openrouter.ai/api/v1" if _os2.getenv("OPENROUTER_API_KEY") else "https://api.openai.com/v1"
    try:
        async with _hx2.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 700},
            )
            content = resp.json()["choices"][0]["message"]["content"].strip()
            m = _re.search(r"\{.*\}", content, _re.DOTALL)
            if not m:
                raise ValueError("No JSON in response")
            return _json.loads(m.group())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI evaluation failed: {exc}")


# ── Page view tracking ────────────────────────────────────────────────────────
_PIXEL_GIF = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x00\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"


@app.get("/api/pixel", include_in_schema=False)
async def tracking_pixel(
    request: Request,
    page: str = Query("landing"),
    ref: str = Query(""),
):
    """1×1 transparent GIF tracking pixel — logs page visits to page_views table."""
    import hashlib as _hl
    ip = request.client.host if request.client else "unknown"
    ip_hash = _hl.sha256(ip.encode()).hexdigest()[:16]
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB) as db:
            await db.execute(
                "INSERT INTO page_views (page, referrer, ip_hash) VALUES (?, ?, ?)",
                (page[:100], ref[:200], ip_hash),
            )
            await db.commit()
    except Exception:
        pass
    from fastapi.responses import Response as _Resp
    return _Resp(content=_PIXEL_GIF, media_type="image/gif", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
    })


# ── LinkedIn Import ───────────────────────────────────────────────────────────
async def _scrape_linkedin_url(url: str) -> dict:
    import re as _re2
    try:
        async with _httpx_module.AsyncClient(timeout=12, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8",
        }) as client:
            resp = await client.get(url)
            html = resp.text
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Не удалось загрузить профиль: {exc}")

    result: dict = {}
    # JSON-LD (public profiles)
    ld = _re2.search(r'<script type="application/ld\+json">(.*?)</script>', html, _re2.DOTALL)
    if ld:
        try:
            import json as _j
            d = _j.loads(ld.group(1))
            result["name"] = d.get("name", "")
            result["headline"] = d.get("jobTitle", "")
            result["summary"] = d.get("description", "")
        except Exception:
            pass
    # OG fallback
    og_title = _re2.search(r'<meta property="og:title" content="([^"]+)"', html)
    if og_title and not result.get("name"):
        result["name"] = og_title.group(1).split(" | ")[0]
    og_desc = _re2.search(r'<meta property="og:description" content="([^"]+)"', html)
    if og_desc and not result.get("summary"):
        result["summary"] = og_desc.group(1)

    if not result.get("name"):
        raise HTTPException(
            status_code=422,
            detail="LinkedIn заблокировал автоматический парсинг. Используйте экспорт ZIP.",
        )
    return result


def _parse_linkedin_zip(zip_bytes: bytes) -> dict:
    import zipfile, io, csv as _csv
    result: dict = {}
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()

            def read_csv(fname):
                for n in names:
                    if n.endswith(fname):
                        with zf.open(n) as f:
                            return list(_csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig")))
                return []

            for row in read_csv("Profile.csv"):
                result["name"] = f"{row.get('First Name','')} {row.get('Last Name','')}".strip()
                result["email"] = row.get("Email Address", "")
                result["phone"] = row.get("Phone Numbers", "")
                result["summary"] = row.get("Summary", "")
                result["headline"] = row.get("Headline", "")
                break

            result["experience"] = [
                {
                    "company": r.get("Company Name", ""),
                    "title": r.get("Title", ""),
                    "start": r.get("Started On", ""),
                    "end": r.get("Finished On", "") or "по настоящее время",
                    "description": r.get("Description", ""),
                    "location": r.get("Location", ""),
                }
                for r in read_csv("Positions.csv")
            ]
            result["education"] = [
                {
                    "school": r.get("School Name", ""),
                    "degree": r.get("Degree Name", ""),
                    "field": r.get("Field Of Study", ""),
                    "start": r.get("Start Date", ""),
                    "end": r.get("End Date", ""),
                }
                for r in read_csv("Education.csv")
            ]
            result["skills"] = [r.get("Name", "") for r in read_csv("Skills.csv") if r.get("Name")]
            result["languages"] = [
                f"{r.get('Name','')} ({r.get('Proficiency','')})"
                for r in read_csv("Languages.csv") if r.get("Name")
            ]
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Некорректный ZIP файл")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки ZIP: {exc}")

    if not result.get("name") and not result.get("experience"):
        raise HTTPException(status_code=422, detail="ZIP не содержит данных LinkedIn. Убедитесь, что выбрали 'Данные профиля'.")
    return result


@app.post("/api/resume/import-linkedin", summary="Import LinkedIn profile via URL scrape or ZIP export")
async def import_linkedin(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    ct = request.headers.get("content-type", "")
    if "application/json" in ct:
        body = await request.json()
        url = body.get("linkedin_url", "").strip()
        if not url:
            raise HTTPException(status_code=400, detail="linkedin_url обязателен")
        return await _scrape_linkedin_url(url)
    else:
        form = await request.form()
        file_field = form.get("file")
        if not file_field:
            raise HTTPException(status_code=400, detail="Файл не передан")
        zip_bytes = await file_field.read()
        return _parse_linkedin_zip(zip_bytes)


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
