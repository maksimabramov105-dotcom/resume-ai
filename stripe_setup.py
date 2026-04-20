#!/usr/bin/env python3
"""
stripe_setup.py — One-time Stripe product and price creation.

Run once to bootstrap products/prices on a new Stripe account:
    python stripe_setup.py

Prints the price IDs to add to your .env:
    STRIPE_PRICE_TRIAL=price_xxx
    STRIPE_PRICE_PRO_MONTHLY=price_xxx
    STRIPE_PRICE_PRO_ANNUAL=price_xxx
    STRIPE_PRICE_PREMIUM_MONTHLY=price_xxx
    STRIPE_PRICE_PREMIUM_ANNUAL=price_xxx
"""

import os
import sys

try:
    import stripe
except ImportError:
    print("Install stripe first: pip install stripe")
    sys.exit(1)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
if not stripe.api_key:
    print("ERROR: STRIPE_SECRET_KEY not set in environment.")
    sys.exit(1)

PRODUCTS = [
    {
        "name": "ResumeAI Trial",
        "description": "14-day trial — up to 30 auto-applications",
        "prices": [
            {
                "env_key": "STRIPE_PRICE_TRIAL",
                "amount": 299,
                "currency": "usd",
                "recurring": None,
                "nickname": "Trial 14 days",
            }
        ],
    },
    {
        "name": "ResumeAI Pro",
        "description": "50 auto-applications per day — LinkedIn, Greenhouse, Lever, Workable",
        "prices": [
            {
                "env_key": "STRIPE_PRICE_PRO_MONTHLY",
                "amount": 1999,
                "currency": "usd",
                "recurring": "month",
                "nickname": "Pro Monthly",
            },
            {
                "env_key": "STRIPE_PRICE_PRO_ANNUAL",
                "amount": 19190,
                "currency": "usd",
                "recurring": "year",
                "nickname": "Pro Annual (20% off)",
            },
        ],
    },
    {
        "name": "ResumeAI Premium",
        "description": "Unlimited auto-applications per day — all ATS platforms",
        "prices": [
            {
                "env_key": "STRIPE_PRICE_PREMIUM_MONTHLY",
                "amount": 2999,
                "currency": "usd",
                "recurring": "month",
                "nickname": "Premium Monthly",
            },
            {
                "env_key": "STRIPE_PRICE_PREMIUM_ANNUAL",
                "amount": 28790,
                "currency": "usd",
                "recurring": "year",
                "nickname": "Premium Annual (20% off)",
            },
        ],
    },
]


def find_existing_product(name: str):
    products = stripe.Product.list(limit=100)
    for p in products.auto_paging_iter():
        if p.name == name and p.active:
            return p
    return None


def find_existing_price(product_id: str, amount: int, recurring_interval):
    prices = stripe.Price.list(product=product_id, limit=100)
    for p in prices.auto_paging_iter():
        if p.unit_amount == amount:
            if recurring_interval is None and p.type == "one_time":
                return p
            if recurring_interval and p.recurring and p.recurring.interval == recurring_interval:
                return p
    return None


def main():
    print(f"Connected to Stripe account: {stripe.api_key[:12]}...")
    print()

    env_lines = []

    for product_def in PRODUCTS:
        print(f"Product: {product_def['name']}")

        existing = find_existing_product(product_def["name"])
        if existing:
            product = existing
            print(f"  ✓ Already exists: {product.id}")
        else:
            product = stripe.Product.create(
                name=product_def["name"],
                description=product_def["description"],
                metadata={"app": "resumeai-bot"},
            )
            print(f"  + Created: {product.id}")

        for price_def in product_def["prices"]:
            existing_price = find_existing_price(
                product.id, price_def["amount"], price_def["recurring"]
            )
            if existing_price:
                price = existing_price
                print(f"  ✓ Price already exists ({price_def['nickname']}): {price.id}")
            else:
                price_kwargs = {
                    "product": product.id,
                    "unit_amount": price_def["amount"],
                    "currency": price_def["currency"],
                    "nickname": price_def["nickname"],
                    "metadata": {"app": "resumeai-bot"},
                }
                if price_def["recurring"]:
                    price_kwargs["recurring"] = {"interval": price_def["recurring"]}

                price = stripe.Price.create(**price_kwargs)
                print(f"  + Created price ({price_def['nickname']}): {price.id}")

            env_lines.append(f"{price_def['env_key']}={price.id}")

        print()

    print("=" * 60)
    print("Add these to your .env file on the VPS:")
    print("=" * 60)
    for line in env_lines:
        print(line)
    print()
    print("Then restart the autoapply service:")
    print("  sudo systemctl restart autoapply")


if __name__ == "__main__":
    main()
