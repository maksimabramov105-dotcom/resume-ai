#!/usr/bin/env python3
"""
reconcile_payments.py — Cross-check Stripe subscriptions against autoapply.db

Usage:
  python3 scripts/reconcile_payments.py            # report only
  python3 scripts/reconcile_payments.py --fix       # report + auto-fix mismatches
  python3 scripts/reconcile_payments.py --fix --dry # dry-run (show SQL, don't execute)

Requires: STRIPE_SECRET_KEY and AUTOAPPLY_DB env vars (or .env file at project root).
"""
import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load .env from project root if present
_root = Path(__file__).parent.parent
_env = _root / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

try:
    import stripe
except ImportError:
    sys.exit("stripe package not installed — run: pip install stripe")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
AUTOAPPLY_DB = os.getenv("AUTOAPPLY_DB", "/opt/resumeaibot/autoapply.db")

if not STRIPE_SECRET_KEY:
    sys.exit("STRIPE_SECRET_KEY not set")

stripe.api_key = STRIPE_SECRET_KEY

TIER_MAP = {
    # Maps Stripe product/price metadata tier → plan name in DB
    "trial": "trial",
    "pro": "pro",
    "unlimited": "unlimited",
}
PAID_TIERS = {"trial", "pro", "unlimited"}


def fetch_stripe_subscriptions() -> dict[str, dict]:
    """
    Returns {stripe_customer_id: {status, tier, current_period_end}}.
    Only includes subscriptions with metadata.tier set.
    """
    print("Fetching Stripe subscriptions…")
    subs: dict[str, dict] = {}
    for sub in stripe.Subscription.list(limit=100, expand=["data.customer"]).auto_paging_iter():
        tier = (sub.get("metadata") or {}).get("tier") or ""
        # Also check checkout session metadata stored in subscription
        if not tier:
            for item in sub.get("items", {}).get("data", []):
                price_meta = (item.get("price") or {}).get("metadata") or {}
                tier = price_meta.get("tier", "")
                if tier:
                    break
        customer_id = sub.get("customer")
        if isinstance(customer_id, dict):
            customer_id = customer_id.get("id", "")
        subs[customer_id] = {
            "status": sub.get("status"),          # active, past_due, canceled, etc.
            "tier": tier or "pro",                 # default to pro if metadata missing
            "period_end": sub.get("current_period_end"),
            "sub_id": sub.get("id"),
        }
    print(f"  Found {len(subs)} Stripe subscription(s)")
    return subs


def fetch_db_users(db_path: str) -> list[dict]:
    """Returns all autoapply_users rows with stripe_customer_id set."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, email, telegram_id, plan, stripe_customer_id FROM autoapply_users"
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.OperationalError as e:
        print(f"[WARN] DB query error: {e}")
        return []
    finally:
        conn.close()


def run_fix(db_path: str, user_id: int, new_plan: str, dry: bool) -> None:
    label = "DRY" if dry else "FIXED"
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    sql = f"UPDATE autoapply_users SET plan='{new_plan}', daily_limit=999 WHERE id={user_id}"
    print(f"  [{label}] {sql}")
    if not dry:
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                "UPDATE autoapply_users SET plan=? WHERE id=?",
                (new_plan, user_id),
            )
            conn.commit()
        finally:
            conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconcile Stripe subscriptions with DB")
    parser.add_argument("--fix", action="store_true", help="Apply fixes")
    parser.add_argument("--dry", action="store_true", help="Dry-run (with --fix)")
    args = parser.parse_args()

    stripe_subs = fetch_stripe_subscriptions()
    db_users = fetch_db_users(AUTOAPPLY_DB)

    print(f"\nDB users: {len(db_users)}")
    print("=" * 60)

    issues: list[str] = []
    fixes: int = 0

    for user in db_users:
        uid = user["id"]
        email = user["email"] or "?"
        db_plan = user["plan"] or "free"
        cid = user["stripe_customer_id"] or ""

        if not cid:
            if db_plan in PAID_TIERS:
                msg = f"  [WARN] user {uid} ({email}) has plan={db_plan} but NO stripe_customer_id"
                issues.append(msg)
                print(msg)
            continue

        stripe_info = stripe_subs.get(cid)
        if not stripe_info:
            if db_plan in PAID_TIERS:
                msg = f"  [MISMATCH] user {uid} ({email}) plan={db_plan} but Stripe customer {cid} has NO subscription"
                issues.append(msg)
                print(msg)
                if args.fix:
                    run_fix(AUTOAPPLY_DB, uid, "free", args.dry)
                    fixes += 1
            continue

        stripe_status = stripe_info["status"]
        stripe_tier = stripe_info["tier"]

        # Stripe active but DB is free → activate
        if stripe_status == "active" and db_plan == "free":
            msg = f"  [MISMATCH] user {uid} ({email}) Stripe={stripe_tier}/active but DB=free"
            issues.append(msg)
            print(msg)
            if args.fix:
                run_fix(AUTOAPPLY_DB, uid, stripe_tier, args.dry)
                fixes += 1

        # Stripe cancelled/expired but DB shows paid → downgrade
        elif stripe_status in ("canceled", "unpaid", "past_due") and db_plan in PAID_TIERS:
            msg = f"  [MISMATCH] user {uid} ({email}) Stripe={stripe_status} but DB={db_plan}"
            issues.append(msg)
            print(msg)
            if args.fix:
                run_fix(AUTOAPPLY_DB, uid, "free", args.dry)
                fixes += 1

        else:
            print(f"  [OK] user {uid} ({email}) DB={db_plan} Stripe={stripe_tier}/{stripe_status}")

    print("=" * 60)
    if issues:
        print(f"TOTAL ISSUES: {len(issues)}")
        if args.fix:
            print(f"FIXES APPLIED: {fixes}" + (" (DRY RUN)" if args.dry else ""))
    else:
        print("All users reconciled — no mismatches found ✅")


if __name__ == "__main__":
    main()
