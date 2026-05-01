#!/usr/bin/env bash
# backup_db.sh — hot SQLite backup using sqlite3 Online Backup API (.backup command)
# WAL-safe: consistent snapshot even under concurrent writes.
# Runs via systemd backup-db.timer (every 6h) OR cron fallback.
#
# Cron fallback (if timer not installed):
#   0 */6 * * * /opt/resumeaibot/scripts/backup_db.sh >> /opt/resumeaibot/logs/backup.log 2>&1

set -euo pipefail

TIMESTAMP=$(date +"%F-%H%M")
DB_DIR="/opt/resumeaibot"
BACKUP_DIR="/opt/resumeaibot/backups"
KEEP_DAYS=14

mkdir -p "$BACKUP_DIR"

echo "=== Backup started at $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="

backup_db() {
    local src="$1"
    local name="$2"
    local dest="${BACKUP_DIR}/${name}.${TIMESTAMP}.db"

    if [ ! -f "$src" ]; then
        echo "[SKIP] $src not found"
        return 0
    fi

    sqlite3 "$src" ".backup '${dest}'"
    local size
    size=$(du -sh "$dest" | cut -f1)
    echo "[OK] ${name} → ${dest} (${size})"
}

backup_db "${DB_DIR}/bot.db"        "bot"
backup_db "${DB_DIR}/autoapply.db"  "autoapply"

# Prune backups older than KEEP_DAYS
pruned=$(find "$BACKUP_DIR" -name "*.db" -mtime +"$KEEP_DAYS" -print -delete | wc -l)
echo "[PRUNE] removed ${pruned} backup(s) older than ${KEEP_DAYS} days"

# ── Offsite (S3) — uncomment after adding AWS_BACKUP_BUCKET to .env ──────────
# Requires: aws-cli installed, AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY in .env
# if [ -n "${AWS_BACKUP_BUCKET:-}" ]; then
#     aws s3 sync "$BACKUP_DIR/" "s3://${AWS_BACKUP_BUCKET}/resumeaibot/" \
#         --exclude "*" --include "*.db" --storage-class STANDARD_IA \
#         && echo "[S3] synced to s3://${AWS_BACKUP_BUCKET}/resumeaibot/" \
#         || echo "[S3] WARNING: S3 sync failed (local backups intact)"
# fi

echo "=== Backup finished at $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="

# ── Telegram notification (offsite awareness, no file transfer) ───────────────
if [ -n "${BOT_TOKEN:-}" ] && [ -n "${ADMIN_TELEGRAM_ID:-}" ]; then
    BOT_SIZE=$(du -sh "${BACKUP_DIR}/bot.${TIMESTAMP}.db"       2>/dev/null | cut -f1 || echo "?")
    AA_SIZE=$(du -sh  "${BACKUP_DIR}/autoapply.${TIMESTAMP}.db" 2>/dev/null | cut -f1 || echo "?")
    BOT_SHA=$(sha256sum "${BACKUP_DIR}/bot.${TIMESTAMP}.db"       2>/dev/null | cut -c1-12 || echo "?")
    AA_SHA=$(sha256sum  "${BACKUP_DIR}/autoapply.${TIMESTAMP}.db" 2>/dev/null | cut -c1-12 || echo "?")
    MSG="✅ DB backup ${TIMESTAMP}%0Abot.db: ${BOT_SIZE} (sha256: ${BOT_SHA}...)%0Aautoapply.db: ${AA_SIZE} (sha256: ${AA_SHA}...)%0APruned: ${pruned} old file(s)"
    curl -fsS --max-time 10 \
        "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage?chat_id=${ADMIN_TELEGRAM_ID}&text=${MSG}" \
        > /dev/null 2>&1 || echo "[WARN] Telegram notification failed (backup intact)"
fi
