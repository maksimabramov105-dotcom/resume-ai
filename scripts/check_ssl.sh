#!/usr/bin/env bash
# check_ssl.sh — verify SSL certificate is not expiring soon.
# Alerts via Telegram if cert expires within WARN_DAYS.
# Run via cron (weekly):
#   0 8 * * 1  /opt/resumeaibot/scripts/check_ssl.sh >> /opt/resumeaibot/logs/ssl_check.log 2>&1
set -euo pipefail

DOMAIN="${DOMAIN:-resumeai-bot.ru}"
WARN_DAYS="${WARN_DAYS:-21}"
BOT_TOKEN="${BOT_TOKEN:-}"
ADMIN_TELEGRAM_ID="${ADMIN_TELEGRAM_ID:-}"

log() { echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"; }

_tg_alert() {
    local msg="$1"
    if [[ -n "$BOT_TOKEN" && -n "$ADMIN_TELEGRAM_ID" ]]; then
        curl -fsS -X POST \
             "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
             -d chat_id="${ADMIN_TELEGRAM_ID}" \
             -d text="${msg}" \
             -d parse_mode="Markdown" > /dev/null || true
    fi
}

# ── 1. Check via openssl ─────────────────────────────────────────────────────
EXPIRY=$(echo | openssl s_client -connect "${DOMAIN}:443" -servername "${DOMAIN}" 2>/dev/null \
    | openssl x509 -noout -enddate 2>/dev/null \
    | cut -d= -f2)

if [[ -z "$EXPIRY" ]]; then
    msg="⚠️ SSL check FAILED for ${DOMAIN} — could not retrieve certificate"
    log "$msg"
    _tg_alert "$msg"
    exit 1
fi

EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$EXPIRY" +%s 2>/dev/null)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - NOW_EPOCH) / 86400 ))

log "SSL cert for ${DOMAIN}: expires ${EXPIRY} (${DAYS_LEFT} days)"

if [[ "$DAYS_LEFT" -lt "$WARN_DAYS" ]]; then
    msg="🔴 *SSL cert expiring soon!*\nDomain: \`${DOMAIN}\`\nExpiry: ${EXPIRY}\nDays left: ${DAYS_LEFT}\n\nRun: \`certbot renew --force-renewal\`"
    log "WARNING: $msg"
    _tg_alert "$msg"
    exit 2
fi

log "OK — ${DAYS_LEFT} days remaining (threshold: ${WARN_DAYS})"

# ── 2. Trigger certbot dry-run (weekly — just to keep renewal working) ───────
if command -v certbot >/dev/null 2>&1; then
    certbot renew --dry-run --quiet 2>&1 | head -5 || log "certbot dry-run returned non-zero (check manually)"
fi

log "SSL check complete"
