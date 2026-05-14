"""
common.py — Shared helpers for autoapply modules.

Provides:
  - _clean_user_data()  : validate / normalise user_data dicts before submission
  - not_available_result(): standard error dict when a dependency is missing
"""
from typing import Any


def not_available_result(reason: str, context: str = "") -> dict[str, Any]:
    """Return a standardised error dict when a required dependency is unavailable."""
    return {
        "success": False,
        "status": "error",
        "error": reason,
        "context": context,
    }


def clean_user_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Normalise and fill defaults for user_data passed to ATS fillers.

    Expected keys (all optional — defaults provided):
        first_name, last_name, email, phone, linkedin_url,
        resume_text, cover_letter, current_company,
        portfolio_url, location, experience_years
    """
    name = data.get("name", "")
    parts = name.strip().split() if name else []

    return {
        "first_name": data.get("first_name") or (parts[0] if parts else ""),
        "last_name": data.get("last_name") or (" ".join(parts[1:]) if len(parts) > 1 else ""),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "linkedin_url": data.get("linkedin_url", ""),
        "resume_text": data.get("resume_text", ""),
        "cover_letter": data.get("cover_letter", ""),
        "current_company": data.get("current_company", ""),
        "portfolio_url": data.get("portfolio_url", ""),
        "location": data.get("location", ""),
        "experience_years": str(data.get("experience_years", "1")),
    }
