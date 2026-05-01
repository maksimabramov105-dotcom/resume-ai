#!/usr/bin/env bash
# deploy.sh — sync local git checkout → server, then restart services.
# SAFE: never uses --delete-excluded (would wipe .env, .venv, *.db, backups, logs).
# Never call this with --delete-excluded. Excluded files on server are preserved.
set -euo pipefail

SERVER="root@72.56.250.53"
REMOTE_DIR="/opt/resumeaibot"
LOCAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Deploy: $LOCAL_DIR → $SERVER:$REMOTE_DIR ==="

# SSH wrapper (replace with key-based auth after SSH hardening)
SSH_CMD="sshpass -p '${VPS_PASS:?Set VPS_PASS env var}' ssh -o StrictHostKeyChecking=no"

rsync -az --delete-after \
  --exclude='.git' \
  --exclude='.env' \
  --exclude='.venv' \
  --exclude='*.db' \
  --exclude='backups/' \
  --exclude='logs/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='audit/' \
  --exclude='node_modules/' \
  --exclude='.DS_Store' \
  -e "$SSH_CMD" \
  "$LOCAL_DIR/" \
  "$SERVER:$REMOTE_DIR/"

echo "=== Rsync complete — restarting services ==="
eval "$SSH_CMD" "$SERVER" "
  mkdir -p $REMOTE_DIR/logs $REMOTE_DIR/backups
  systemctl restart resumeaibot autoapply autoapply-worker
  sleep 6
  systemctl is-active resumeaibot autoapply autoapply-worker
  echo '--- health ---'
  curl -fsS http://localhost:8000/api/health && echo
  curl -fsS http://localhost:8080/api/health && echo
"
echo "=== Deploy done ==="
