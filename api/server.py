import logging
import sys
import os

# Make bot/ importable from api/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot'))

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from api.routes import user, resume, cover_letter, interview, vacancy, assistant, payment, stripe

logger = logging.getLogger(__name__)

# ── Sentry (graceful no-op if SENTRY_DSN not set) ────────────────────────────
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1, integrations=[FastApiIntegration()])
    logger.info("Sentry initialised (api/server.py)")

app = FastAPI(title="РезюмеАИ API", version="1.0")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s: %s", request.method, request.url.path, exc)
    if _sentry_dsn:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    return JSONResponse(status_code=500, content={"error": "internal_server_error"})

_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "https://resumeai-bot.ru,https://www.resumeai-bot.ru,https://web.telegram.org",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Telegram-Init-Data"],
)

app.include_router(user.router,         prefix="/api/user",         tags=["User"])
app.include_router(resume.router,       prefix="/api/resume",       tags=["Resume"])
app.include_router(cover_letter.router, prefix="/api/cover-letter", tags=["Cover Letter"])
app.include_router(interview.router,    prefix="/api/interview",     tags=["Interview"])
app.include_router(vacancy.router,      prefix="/api/vacancy",       tags=["Vacancy"])
app.include_router(assistant.router,    prefix="/api/assistant",     tags=["Assistant"])
app.include_router(payment.router,      prefix="/api/payment",       tags=["Payment"])
app.include_router(stripe.router,       prefix="/api/stripe",        tags=["Stripe"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "bot": "РезюмеАИ"}


# Serve React build (added last so /api routes take priority)
webapp_build = os.path.join(os.path.dirname(__file__), '..', 'webapp', 'dist')
if os.path.exists(webapp_build):
    app.mount("/", StaticFiles(directory=webapp_build, html=True), name="webapp")
