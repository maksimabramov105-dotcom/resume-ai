#!/usr/bin/env bash
# backup_db.sh — hot SQLite backup using .backup command (safe under concurrent writes)
# Runs via cron every 6 hours. Keeps 7 days of rolling backups locally + rsync to off-VPS.
#
# Cron entry (add with: crontab -e):
#   0 */6 * * * /opt/resumeaibot/scripts/backup_db.sh >> /opt/resumeaibot/logs/backup.log 2>&1

set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_DIR="/opt/resumeaibot"
BACKUP_DIR="/opt/resumeaibot/backups"
KEEP_DAYS=7

mkdir -p "$BACKUP_DIR"

backup_db() {
    local src="$1"
    local name="$2"
    local dest="$BACKUP_DIR/${name}_${TIMESTAMP}.db"

    if [ ! -f "$src" ]; then
        echo "[SKIP] $src not found"
        return
    fi

    # Use Python sqlite3.connect().backup() — WAL-safe, no external tool needed
    python3 - "$src" "$dest" <<'PYEOF'
import sys, sqlite3
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(src) as s, sqlite3.connect(dst) as d:
    s.backup(d)
PYEOF
    local size
    size=$(du -sh "$dest" | cut -f1)
    echo "[OK] $name → $dest ($size)"
}

echo "=== Backup started at $(date) ==="

backup_db "$DB_DIR/autoapply.db" "autoapply"
backup_db "$DB_DIR/bot.db"       "bot"

# Prune backups older than KEEP_DAYS
find "$BACKUP_DIR" -name "*.db" -mtime +"$KEEP_DAYS" -delete
echo "[PRUNE] removed backups older than ${KEEP_DAYS} days"

# Optional: rsync to a remote target
# Uncomment and set REMOTE_HOST + REMOTE_PATH if you have an off-VPS destination.
# REMOTE_HOST="user@backup-server.example.com"
# REMOTE_PATH="/backups/resumeaibot/"
# if rsync -az --delete "$BACKUP_DIR/" "$REMOTE_HOST:$REMOTE_PATH" 2>/dev/null; then
#     echo "[RSYNC] synced to $REMOTE_HOST:$REMOTE_PATH"
# else
#     echo "[RSYNC] WARNING: remote sync failed (backups still local)"
# fi

echo "=== Backup finished at $(date) ==="
