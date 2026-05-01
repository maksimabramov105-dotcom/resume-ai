# Incident Runbook: Bot / API Down

**Symptoms:** Telegram bot not responding · `/api/health` returns non-200 · Monitor alert fires

---

## 1 · Immediate triage (< 2 min)

```bash
VPS="root@72.56.250.53"
PASS="iY_.E8rWwaMRMA"
SSH="sshpass -p '$PASS' ssh -o StrictHostKeyChecking=no $VPS"

# What's the status of all three services?
eval "$SSH" "systemctl is-active resumeaibot autoapply autoapply-worker"

# Quick health endpoints
eval "$SSH" "curl -fsS http://localhost:8000/api/health 2>&1 | head -1"
eval "$SSH" "curl -fsS http://localhost:8080/api/health 2>&1 | head -1"
```

---

## 2 · Service-specific fixes

### 2a — `resumeaibot.service` down (Telegram bot, port 8000)

```bash
# Check why it stopped
eval "$SSH" "journalctl -u resumeaibot -n 50 --no-pager"
eval "$SSH" "systemctl status resumeaibot"

# Common causes:
#   exit 203/EXEC  → .venv missing  →  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
#   exit 209/STDOUT → logs/ missing  →  mkdir -p /opt/resumeaibot/logs && touch /opt/resumeaibot/logs/bot.log
#   ImportError     → bad deploy     →  git checkout HEAD -- bot/  && redeploy
#   BOT_TOKEN empty → .env missing   →  recreate .env from /proc/<PID>/environ (see below)

# Restart
eval "$SSH" "systemctl restart resumeaibot && sleep 4 && systemctl is-active resumeaibot"
```

### 2b — `autoapply.service` down (FastAPI, port 8080)

```bash
eval "$SSH" "journalctl -u autoapply -n 50 --no-pager"
eval "$SSH" "systemctl restart autoapply && sleep 4 && curl -fsS http://localhost:8080/api/health"
```

### 2c — `autoapply-worker.service` down

```bash
eval "$SSH" "journalctl -u autoapply-worker -n 30 --no-pager"
eval "$SSH" "systemctl restart autoapply-worker"
```

---

## 3 · .env missing or corrupt

If `.env` was accidentally deleted:

```bash
# Recover from running process environment (works while process is still up)
eval "$SSH" "
  PID=\$(systemctl show -p MainPID autoapply | cut -d= -f2)
  cat /proc/\$PID/environ | tr '\0' '\n' | grep -E '^(BOT_TOKEN|JWT_SECRET|OPENAI|STRIPE|CRYPTOBOT|SMTP|ENCRYPTION_KEY|ADMIN|WEBAPP)' > /tmp/recovered.env
  cat /tmp/recovered.env
"
# Then reconstruct /opt/resumeaibot/.env from /tmp/recovered.env output
```

If the process is already dead, restore from the most recent backup or `.env.example`.

---

## 4 · Database issues

```bash
# Check DB file exists and is readable
eval "$SSH" "ls -lh /opt/resumeaibot/*.db"
eval "$SSH" "sqlite3 /opt/resumeaibot/autoapply.db 'PRAGMA integrity_check;'"

# WAL recovery (if DB locked after crash)
eval "$SSH" "sqlite3 /opt/resumeaibot/autoapply.db 'PRAGMA wal_checkpoint(FULL);'"

# Full restore from backup (last resort)
# See: docs/runbooks/restore-db.md
```

---

## 5 · Disk full

```bash
eval "$SSH" "df -h / && du -sh /opt/resumeaibot/logs/* | sort -h | tail -10"

# Truncate largest log files (safe — services reopen on write)
eval "$SSH" "truncate -s 0 /opt/resumeaibot/logs/autoapply_api.log"
eval "$SSH" "truncate -s 0 /opt/resumeaibot/logs/worker.log"
```

---

## 6 · .venv corrupted / missing

```bash
eval "$SSH" "
  cd /opt/resumeaibot
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip -q
  .venv/bin/pip install -r requirements.txt -q
  systemctl restart resumeaibot autoapply autoapply-worker
"
```

---

## 7 · nginx down (landing page 502/504)

```bash
eval "$SSH" "systemctl is-active nginx || systemctl start nginx"
eval "$SSH" "nginx -t && systemctl reload nginx"
eval "$SSH" "curl -fsS https://resumeai-bot.ru/ -o /dev/null -w '%{http_code}\n'"
```

---

## 8 · SSL certificate expired

```bash
eval "$SSH" "certbot renew --force-renewal && systemctl reload nginx"
# Or check status:
eval "$SSH" "certbot certificates"
```

---

## 9 · Telegram webhook broken

```bash
BOT_TOKEN="<from .env>"
# Re-register webhook
curl "https://api.telegram.org/bot$BOT_TOKEN/setWebhook" \
  -d "url=https://resumeai-bot.ru/webhook/$BOT_TOKEN"
# Verify
curl "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo"
```

---

## Escalation

If none of the above resolves it within 15 min:
1. Check VPS provider dashboard for host-level outages
2. Telegram: notify @resumeai_support channel
3. Set `AUTOAPPLY_ENABLED=0` in `.env` + restart autoapply-worker to stop applying while debugging
