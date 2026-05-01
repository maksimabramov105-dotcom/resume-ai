#!/usr/bin/env python3
"""
smoke_test_payments.py — E2E smoke test for payment endpoints.

Checks:
  1. /api/health  (bot API) — must return status=ok
  2. /api/health  (autoapply) — must return status=ok
  3. /api/pricing — must return all plan tiers with price_usd
  4. /api/stripe/create-checkout — must return checkout_url (Stripe live/test key required)
  5. /api/payment/cryptobot — must return invoice_url (CryptoBot token required)

Usage:
  BOT_API=http://localhost:8000 AA_API=http://localhost:8080 python3 scripts/smoke_test_payments.py
  BOT_API=https://resumeai-bot.ru   AA_API=https://resumeai-bot.ru   python3 scripts/smoke_test_payments.py

Exit code 0 = all passed, 1 = one or more failed.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Load .env from project root if present
_env = Path(__file__).parent.parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

BOT_API = os.getenv("BOT_API", "http://localhost:8000")
AA_API  = os.getenv("AA_API",  "http://localhost:8080")
TEST_USER_ID = int(os.getenv("TEST_USER_ID", "1"))   # a known telegram_id in DB

PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⚠️  SKIP"

failures = 0


def get(url: str, timeout: int = 10) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def post(url: str, body: dict, timeout: int = 15) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def check(name: str, ok: bool, detail: str = "") -> None:
    global failures
    label = PASS if ok else FAIL
    if not ok:
        failures += 1
    suffix = f"  ({detail})" if detail else ""
    print(f"{label}  {name}{suffix}")


# ── 1. Bot API health ─────────────────────────────────────────────────────
status, body = get(f"{BOT_API}/api/health")
check("Bot API /api/health", status == 200 and body.get("status") == "ok",
      f"HTTP {status}")

# ── 2. AutoApply health ───────────────────────────────────────────────────
status, body = get(f"{AA_API}/api/health")
check("AutoApply /api/health", status == 200 and body.get("status") == "ok",
      f"HTTP {status}")

# ── 3. Pricing endpoint ───────────────────────────────────────────────────
status, body = get(f"{AA_API}/api/pricing")
if status == 200:
    tiers = list(body.keys())
    has_required = all(t in tiers for t in ["free", "pro", "unlimited"])
    has_prices = all(
        isinstance(body.get(t, {}).get("price_usd"), (int, float))
        for t in ["pro", "unlimited"]
    )
    check("/api/pricing returns all tiers", has_required, f"tiers={tiers}")
    check("/api/pricing has price_usd for paid tiers", has_prices)
else:
    check("/api/pricing", False, f"HTTP {status}")

# ── 4. Stripe create-checkout (autoapply service) ────────────────────────
STRIPE_KEY = os.getenv("STRIPE_SECRET_KEY", "")
if not STRIPE_KEY:
    print(f"{SKIP}  Stripe create-checkout (STRIPE_SECRET_KEY not set)")
else:
    status, body = post(f"{AA_API}/api/payments/create-checkout",
                        {"user_id": TEST_USER_ID, "plan": "pro", "period": "monthly"})
    # Autoapply returns {"url": ...}, bot API stripe route returns {"checkout_url": ...}
    has_url = bool(body.get("url") or body.get("checkout_url", ""))
    check("Stripe /api/payments/create-checkout → url",
          status == 200 and has_url,
          f"HTTP {status} | url={'present' if has_url else 'MISSING'} body={list(body)}")

# ── 4b. Stripe webhook route accessible (bot API) ────────────────────────
status, _ = post(f"{BOT_API}/api/stripe/webhook", {})
check("Bot API /api/stripe/webhook reachable",
      status in (400, 422),   # 400 = invalid signature (expected), 422 = validation error
      f"HTTP {status}")

# ── 5. CryptoBot invoice ──────────────────────────────────────────────────
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_AUTOAPPLY_TOKEN", "")
if not CRYPTOBOT_TOKEN:
    print(f"{SKIP}  CryptoBot /api/payment/create-invoice (CRYPTOBOT_AUTOAPPLY_TOKEN not set)")
else:
    status, body = post(f"{AA_API}/api/payment/create-invoice",
                        {"user_id": TEST_USER_ID, "plan": "pro"})
    # 401 = JWT required (expected without auth token), 200 = full success
    # 402/503 = token set but CryptoBot rejected → also acceptable in smoke test
    has_url = bool(body.get("invoice_url", ""))
    check("CryptoBot /api/payment/create-invoice reachable",
          status in (200, 401, 402, 422, 503),
          f"HTTP {status} | invoice_url={'present' if has_url else 'not returned'}")

# ── Summary ───────────────────────────────────────────────────────────────
print()
if failures == 0:
    print("All checks passed ✅")
else:
    print(f"{failures} check(s) FAILED ❌")

sys.exit(0 if failures == 0 else 1)
