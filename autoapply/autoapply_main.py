"""
autoapply_main.py — FastAPI application for AutoApply web service.
Runs on port 8080. Bot uses 8000, dashboard uses 8501.
"""
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
    create_campaign,
    create_user,
    get_active_campaigns,
    get_applications_for_user,
    get_campaigns_for_user,
    get_dashboard_stats,
    get_user_by_email,
    get_user_by_id,
    init_db,
    update_campaign_status,
    update_user_last_active,
    update_user_plan,
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


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("[autoapply_main] Starting up — initialising DB at %s", AUTOAPPLY_DB)
    await init_db(AUTOAPPLY_DB)
    logger.info("[autoapply_main] DB ready")


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

    existing = await get_user_by_email(body.email, AUTOAPPLY_DB)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

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
        raise HTTPException(status_code=500, detail="Registration failed")

    token = _create_token(user_id)
    logger.info("[api/register] success user_id=%s", user_id)
    return {"token": token, "user_id": user_id}


@app.post("/api/login", summary="Login and get JWT token")
async def login(body: LoginRequest):
    logger.info("[api/login] attempt for email=%s", body.email)

    user = await get_user_by_email(body.email, AUTOAPPLY_DB)
    if not user or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = _create_token(user["id"])
    logger.info("[api/login] success user_id=%s", user["id"])
    return {"token": token, "user_id": user["id"]}


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.get("/api/dashboard", summary="Get dashboard stats")
async def dashboard(current_user: dict = Depends(get_current_user)):
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
