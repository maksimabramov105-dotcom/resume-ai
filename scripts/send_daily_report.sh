#!/bin/bash
# Standalone daily report sender — run by systemd timer at 05:00 UTC (08:00 MSK)
# Completely independent of the bot process.

set -euo pipefail

WORKDIR="/opt/resumeaibot"
LOGFILE="/opt/resumeaibot/logs/daily_report.log"
PYTHON="/usr/bin/python3"

mkdir -p "$(dirname "$LOGFILE")"

echo "=== $(date '+%Y-%m-%d %H:%M:%S UTC') Starting daily report ===" >> "$LOGFILE"

cd "$WORKDIR"

# Load .env
if [ -f "$WORKDIR/.env" ]; then
    set -a
    source "$WORKDIR/.env"
    set +a
fi

# Run the standalone reporter (daily_reporter.py has __main__ block)
if $PYTHON "$WORKDIR/daily_reporter.py" >> "$LOGFILE" 2>&1; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S UTC') Report sent OK ===" >> "$LOGFILE"
else
    EXIT_CODE=$?
    echo "=== $(date '+%Y-%m-%d %H:%M:%S UTC') ERROR: exit code $EXIT_CODE ===" >> "$LOGFILE"
    # Send error alert via Telegram directly
    BOT_TOKEN="${BOT_TOKEN:-}"
    ADMIN_ID="${ADMIN_ID:-6246429438}"
    if [ -n "$BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
            -d "chat_id=${ADMIN_ID}" \
            -d "text=⚠️ Дневной отчёт упал (systemd timer). Проверь: /opt/resumeaibot/logs/daily_report.log" \
            >> "$LOGFILE" 2>&1 || true
    fi
    exit $EXIT_CODE
fi
