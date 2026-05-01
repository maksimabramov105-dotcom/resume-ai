# Incident Runbook: Payment Stuck / Not Processed

**Symptoms:** User paid but plan not upgraded · Stripe webhook silent · CryptoBot invoice pending forever

---

## 1 · Confirm payment actually succeeded

### Stripe
```bash
# Check Stripe dashboard for the customer
# Dashboard → Customers → search by email → check Subscriptions / Payments

# Or via CLI (if stripe CLI installed)
stripe payment_intents list --limit 5
stripe events list --limit 10 --type checkout.session.completed
```

### CryptoBot
```bash
# Check invoice status via API
curl "https://pay.crypt.bot/api/getInvoices?asset=USDT&status=paid" \
  -H "Crypto-Pay-API-Token: <CRYPTOBOT_AUTOAPPLY_TOKEN>"
```

---

## 2 · Check webhook delivery logs

### Stripe webhook
```bash
VPS="root@72.56.250.53"
PASS="iY_.E8rWwaMRMA"
SSH="sshpass -p '$PASS' ssh -o StrictHostKeyChecking=no $VPS"

# FastAPI autoapply logs around payment time
eval "$SSH" "grep -i 'stripe\|webhook\|checkout\|plan' /opt/resumeaibot/logs/autoapply_api.log | tail -30"

# Look for the specific event
eval "$SSH" "grep 'checkout.session.completed' /opt/resumeaibot/logs/autoapply_api.log | tail -10"
```

In Stripe dashboard: **Developers → Webhooks → your endpoint → Recent deliveries**  
Look for delivery failures (red) and retry them manually from the dashboard.

### CryptoBot webhook
```bash
eval "$SSH" "grep -i 'cryptobot\|invoice\|process_payment' /opt/resumeaibot/logs/autoapply_api.log | tail -20"
```

---

## 3 · Manually upgrade a user's plan

If the payment succeeded but webhook failed:

```bash
eval "$SSH" "
  cd /opt/resumeaibot
  .venv/bin/python3 -c \"
import asyncio, sys
sys.path.insert(0,'.')
from autoapply.autoapply_db import get_user_by_email, update_user_plan

async def fix():
    user = await get_user_by_email('USER_EMAIL_HERE')
    if not user:
        print('user not found')
        return
    print('current plan:', user['plan'])
    await update_user_plan(user['id'], 'pro')  # or 'unlimited'
    user = await get_user_by_email('USER_EMAIL_HERE')
    print('new plan:', user['plan'])

asyncio.run(fix())
\"
"
```

---

## 4 · Check idempotency table (duplicate event prevention)

```bash
eval "$SSH" "
  sqlite3 /opt/resumeaibot/autoapply.db '
    SELECT * FROM stripe_events ORDER BY processed_at DESC LIMIT 10;
    SELECT * FROM cryptobot_events ORDER BY processed_at DESC LIMIT 10;
  '
"
```

If the event_id IS in the table but user plan wasn't updated, the processing ran but the DB update failed. Check logs for the error and apply the manual fix from step 3.

If the event_id is NOT in the table, the webhook was never received or rejected with a bad signature.

---

## 5 · Stripe signature verification failing

```bash
eval "$SSH" "grep 'webhook verification failed\|Invalid signature' /opt/resumeaibot/logs/autoapply_api.log | tail -5"
```

**Fix:** Verify `STRIPE_WEBHOOK_SECRET` in `.env` matches the signing secret shown in  
Stripe Dashboard → Developers → Webhooks → your endpoint → Signing secret.

```bash
eval "$SSH" "grep STRIPE_WEBHOOK_SECRET /opt/resumeaibot/.env"
```

---

## 6 · Run reconciliation script

```bash
# Dry run first — shows mismatches without fixing
eval "$SSH" "
  cd /opt/resumeaibot
  STRIPE_SECRET_KEY=\$(grep STRIPE_SECRET_KEY .env | cut -d= -f2) \
  .venv/bin/python3 scripts/reconcile_payments.py --dry
"

# Apply fixes
eval "$SSH" "
  cd /opt/resumeaibot
  STRIPE_SECRET_KEY=\$(grep STRIPE_SECRET_KEY .env | cut -d= -f2) \
  .venv/bin/python3 scripts/reconcile_payments.py --fix
"
```

---

## 7 · Re-send Stripe event manually

In Stripe Dashboard → Developers → Webhooks → Recent deliveries:  
1. Find the failed `checkout.session.completed` event  
2. Click **Resend** — this replays the full webhook call to your endpoint

---

## 8 · User refund (if payment successful but service broken > 24h)

Only humans should issue refunds. From Stripe Dashboard:  
Payments → find the charge → **Refund** button.  
Do NOT issue refunds programmatically without explicit authorization.

---

## Checklist for post-incident

- [ ] User's plan updated in DB and confirmed with them
- [ ] Root cause identified (webhook signature / delivery failure / code bug)
- [ ] Event logged in stripe_events / cryptobot_events idempotency table
- [ ] `scripts/reconcile_payments.py --dry` shows 0 mismatches
- [ ] Stripe webhook endpoint shows 200 on recent deliveries
