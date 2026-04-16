#!/usr/bin/env python3
"""
run_checks.py — Health & sanity check suite for ResumeAI Bot.

Checks performed:
  1. Environment variables (required keys present)
  2. Bot DB reachable + key tables exist
  3. AutoApply DB reachable
  4. /api/health endpoint responds
  5. /api/stats endpoint responds
  6. /api/resume/templates endpoint responds
  7. OpenAI / OpenRouter API key present and valid
  8. Bot token present (format check)
  9. Landing page is served (nginx)
 10. i18n completeness — en dict has same keys as ru dict

Run locally:     python run_checks.py
Run on VPS:      python run_checks.py --host http://localhost:8080

Exit code 0 = all PASS  |  non-zero = at least one FAIL
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime

# ── ANSI colours ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def _ok(label: str, detail: str = "") -> None:
    suffix = f"  {detail}" if detail else ""
    print(f"  {GREEN}✓ PASS{RESET}  {label}{suffix}")


def _fail(label: str, detail: str = "") -> None:
    suffix = f"  ← {detail}" if detail else ""
    print(f"  {RED}✗ FAIL{RESET}  {label}{suffix}")


def _warn(label: str, detail: str = "") -> None:
    suffix = f"  ← {detail}" if detail else ""
    print(f"  {YELLOW}⚠ WARN{RESET}  {label}{suffix}")


# ─────────────────────────────────────────────────────────────────────────────
# Individual checks
# ─────────────────────────────────────────────────────────────────────────────

def check_env_vars() -> int:
    """Returns number of failures."""
    required = [
        "BOT_TOKEN",
        "ADMIN_ID",
    ]
    recommended = [
        "OPENROUTER_API_KEY",
        "OPENAI_API_KEY",
        "CRYPTOBOT_TOKEN",
        "JWT_SECRET",
    ]
    fails = 0
    for k in required:
        if os.getenv(k):
            _ok(f"ENV {k}")
        else:
            _fail(f"ENV {k}", "REQUIRED — bot won't start without this")
            fails += 1
    for k in recommended:
        if os.getenv(k):
            _ok(f"ENV {k}")
        else:
            _warn(f"ENV {k}", "recommended — some features will be disabled")
    return fails


async def check_bot_db() -> int:
    """Check bot SQLite DB."""
    try:
        import aiosqlite
    except ImportError:
        _warn("Bot DB", "aiosqlite not installed — skipping")
        return 0

    db_path = os.path.join(os.path.dirname(__file__), "bot.db")
    if not os.path.exists(db_path):
        _warn("Bot DB", f"not found at {db_path} (may be OK if running elsewhere)")
        return 0
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT count(*) FROM users") as cur:
                row = await cur.fetchone()
                count = row[0] if row else 0
        _ok("Bot DB", f"{count} users")

        # Check language column exists
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("PRAGMA table_info(users)") as cur:
                cols = [r[1] async for r in cur]
        if "language" in cols:
            _ok("Bot DB language column")
        else:
            _fail("Bot DB language column", "ALTER TABLE migration not run yet")
            return 1
        return 0
    except Exception as exc:
        _fail("Bot DB", str(exc))
        return 1


async def check_autoapply_db() -> int:
    try:
        import aiosqlite
    except ImportError:
        return 0
    db_path = os.path.join(os.path.dirname(__file__), "autoapply", "autoapply.db")
    if not os.path.exists(db_path):
        db_path = os.path.join(os.path.dirname(__file__), "autoapply.db")
    if not os.path.exists(db_path):
        _warn("AutoApply DB", "not found locally (may be on VPS)")
        return 0
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute("SELECT count(*) FROM users") as cur:
                row = await cur.fetchone()
        _ok("AutoApply DB", f"{row[0] if row else 0} users")
        return 0
    except Exception as exc:
        _fail("AutoApply DB", str(exc))
        return 1


async def check_http(session, url: str, label: str, expected_key: str | None = None) -> int:
    try:
        async with session.get(url, timeout=8) as resp:
            if resp.status != 200:
                _fail(label, f"HTTP {resp.status}")
                return 1
            if expected_key:
                data = await resp.json()
                if expected_key not in data:
                    _fail(label, f"response missing key '{expected_key}'")
                    return 1
            _ok(label, f"HTTP 200")
            return 0
    except Exception as exc:
        _fail(label, str(exc))
        return 1


async def check_api_key(session) -> int:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        _warn("OpenAI/OpenRouter key", "not set — AI features disabled")
        return 0
    base = "https://openrouter.ai/api/v1" if os.getenv("OPENROUTER_API_KEY") else "https://api.openai.com/v1"
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        async with session.get(f"{base}/models", headers=headers, timeout=8) as resp:
            if resp.status == 200:
                _ok("OpenAI/OpenRouter API key", "valid")
                return 0
            _fail("OpenAI/OpenRouter API key", f"HTTP {resp.status}")
            return 1
    except Exception as exc:
        _fail("OpenAI/OpenRouter API key", str(exc))
        return 1


def check_i18n() -> int:
    """Verify en dict has all keys that ru dict has."""
    fails = 0
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "bot"))
        from utils.bot_translations import STRINGS
        ru_keys = set(STRINGS.get('ru', {}).keys())
        en_keys = set(STRINGS.get('en', {}).keys())
        missing = ru_keys - en_keys
        if missing:
            for k in sorted(missing):
                _fail(f"i18n key missing in 'en'", k)
            fails += len(missing)
        else:
            _ok("i18n completeness", f"{len(ru_keys)} keys, all present in 'en'")
    except Exception as exc:
        _fail("i18n import", str(exc))
        fails += 1
    return fails


def check_bot_token() -> int:
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        _fail("BOT_TOKEN format", "not set")
        return 1
    parts = token.split(":")
    if len(parts) == 2 and parts[0].isdigit() and len(parts[1]) >= 30:
        _ok("BOT_TOKEN format", "looks valid")
        return 0
    _fail("BOT_TOKEN format", "unexpected format (expected <id>:<hash>)")
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────────────────────────────

async def run_all(host: str) -> int:
    try:
        import aiohttp
    except ImportError:
        print(f"{RED}aiohttp not installed — HTTP checks skipped{RESET}")
        aiohttp = None  # type: ignore[assignment]

    total_fails = 0

    print(f"\n{BOLD}ResumeAI Health Checks{RESET}  ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})")
    print(f"  API host: {host}\n")

    # ── Static checks (no network) ────────────────────────────────────────────
    print(f"{BOLD}[1] Environment variables{RESET}")
    total_fails += check_env_vars()

    print(f"\n{BOLD}[2] Bot token format{RESET}")
    total_fails += check_bot_token()

    print(f"\n{BOLD}[3] i18n completeness{RESET}")
    total_fails += check_i18n()

    # ── DB checks ─────────────────────────────────────────────────────────────
    print(f"\n{BOLD}[4] Bot database{RESET}")
    total_fails += await check_bot_db()

    print(f"\n{BOLD}[5] AutoApply database{RESET}")
    total_fails += await check_autoapply_db()

    # ── HTTP checks ───────────────────────────────────────────────────────────
    if aiohttp:
        async with aiohttp.ClientSession() as session:
            print(f"\n{BOLD}[6] API endpoints{RESET}")
            total_fails += await check_http(session, f"{host}/api/health",            "GET /api/health",            "status")
            total_fails += await check_http(session, f"{host}/api/stats",             "GET /api/stats",             "resumes_generated")
            total_fails += await check_http(session, f"{host}/api/resume/templates",  "GET /api/resume/templates")

            print(f"\n{BOLD}[7] Landing page{RESET}")
            total_fails += await check_http(session, f"{host}/",                      "GET /  (landing)")

            print(f"\n{BOLD}[8] AI API key{RESET}")
            total_fails += await check_api_key(session)

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    if total_fails == 0:
        print(f"{GREEN}{BOLD}✓ All checks passed{RESET}")
    else:
        print(f"{RED}{BOLD}✗ {total_fails} check(s) failed{RESET}")
    print()

    return total_fails


def main() -> None:
    # Try to load .env if python-dotenv is available
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
    except ImportError:
        pass

    parser = argparse.ArgumentParser(description="ResumeAI health checks")
    parser.add_argument(
        "--host",
        default="http://localhost:8080",
        help="Base URL for the AutoApply API (default: http://localhost:8080)",
    )
    args = parser.parse_args()

    fails = asyncio.run(run_all(args.host))
    sys.exit(min(fails, 1))


if __name__ == "__main__":
    main()
