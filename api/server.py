import sys
import os

# Make bot/ importable from api/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot'))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from api.routes import user, resume, cover_letter, interview, vacancy, assistant, payment, stripe

app = FastAPI(title="РезюмеАИ API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
