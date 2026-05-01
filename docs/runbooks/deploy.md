# Runbook: Deploy to Production

**Service:** ResumeAI Bot + AutoApply  
**VPS:** `root@72.56.250.53`  
**Deploy time:** ~2 min (rsync + restart)

---

## Quick deploy (standard code change)

```bash
# 1. Commit locally
git add <files> && git commit -m "..."

# 2. Run safe deploy (never uses --delete-excluded)
VPS_PASS='<password>' bash scripts/deploy.sh
```

`deploy.sh` does: rsync → restart resumeaibot + autoapply + autoapply-worker → health check.

---

## Pre-deploy checklist

- [ ] `python3 -m py_compile autoapply/autoapply_main.py autoapply/worker.py` — no syntax errors
- [ ] `.env` on VPS has all required keys (see `.env.example`)
- [ ] No DB migrations that need a backup first (see [restore-db.md](restore-db.md))
- [ ] `pricing.json` consistent with `autoapply/config.py` PLANS fallback

---

## Manual deploy (step by step)

```bash
VPS="root@72.56.250.53"
PASS="iY_.E8rWwaMRMA"

# Rsync (SAFE — never --delete-excluded)
sshpass -p "$PASS" rsync -az --delete-after \
  --exclude='.git' --exclude='.env' --exclude='.venv' \
  --exclude='*.db'  --exclude='backups/' --exclude='logs/' \
  --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='audit/' --exclude='node_modules/' \
  -e "sshpass -p '$PASS' ssh -o StrictHostKeyChecking=no" \
  ./ "$VPS:/opt/resumeaibot/"

# Restart
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "$VPS" \
  "systemctl restart resumeaibot autoapply autoapply-worker"

# Verify (wait ~6s for startup)
sleep 6
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "$VPS" \
  "curl -fsS http://localhost:8080/api/health | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d[\"status\"])'"
```

---

## Deploying a Next.js frontend change

```bash
# 1. Edit frontend/app/**
cd frontend && npm run build   # output → frontend/out/

# 2. Sync to landing/ (DO NOT use --delete; exclude SEO pages)
rsync -a \
  --exclude='blog/' --exclude='resume/' --exclude='locales/' \
  --exclude='google*.html' --exclude='yandex*.html' \
  --exclude='sitemap.xml' --exclude='robots.txt' \
  --exclude='privacy.html' --exclude='terms.html' --exclude='refund.html' \
  frontend/out/ landing/

cd .. && git add landing/ frontend/ && git commit -m "..."

# 3. Deploy as normal (rsync picks up landing/ changes)
VPS_PASS='...' bash scripts/deploy.sh
```

---

## Deploying nginx config changes

```bash
VPS="root@72.56.250.53"
PASS="iY_.E8rWwaMRMA"

# 1. Edit ops/nginx/resumeai-domain.conf or ops/nginx/rate_limit.conf
# 2. Sync to VPS
sshpass -p "$PASS" rsync -az \
  -e "sshpass -p '$PASS' ssh -o StrictHostKeyChecking=no" \
  ops/nginx/ "$VPS:/opt/resumeaibot/ops/nginx/"

# 3. Apply on server
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "$VPS" "
  cp /opt/resumeaibot/ops/nginx/resumeai-domain.conf /etc/nginx/sites-available/resumeai-domain
  cp /opt/resumeaibot/ops/nginx/rate_limit.conf /etc/nginx/conf.d/rate_limit.conf
  nginx -t && systemctl reload nginx && echo 'nginx OK'
"
```

---

## Post-deploy verification

```bash
# API health
curl https://resumeai-bot.ru/api/health

# Bot webhook still registered (Telegram)
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo" | python3 -m json.tool

# Services active
sshpass -p "$PASS" ssh root@72.56.250.53 \
  "systemctl is-active resumeaibot autoapply autoapply-worker"
```

---

## Rollback

```bash
# Git: identify last good commit
git log --oneline -10

# Deploy specific commit
git checkout <sha> -- autoapply/ bot/ api/
VPS_PASS='...' bash scripts/deploy.sh
git checkout main
```
