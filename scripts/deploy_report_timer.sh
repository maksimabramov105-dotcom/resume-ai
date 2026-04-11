#!/bin/bash
# Run this ONCE on VPS to install the systemd timer for daily reports.
# After this, reports come every day at 08:00 MSK automatically.
# The timer survives reboots, bot crashes, and hardware failures.

set -e

echo "=== Installing ResumeAI daily report timer ==="

# 1. Copy files
mkdir -p /opt/resumeaibot/scripts
cp /opt/resumeaibot/scripts/send_daily_report.sh /opt/resumeaibot/scripts/
chmod +x /opt/resumeaibot/scripts/send_daily_report.sh

# 2. Install systemd units
cp /opt/resumeaibot/scripts/resumeai-report.service /etc/systemd/system/
cp /opt/resumeaibot/scripts/resumeai-report.timer /etc/systemd/system/

# 3. Reload + enable + start timer
systemctl daemon-reload
systemctl enable resumeai-report.timer
systemctl start resumeai-report.timer

# 4. Also deploy updated run.py and start.py
systemctl restart resumeaibot

# 5. Show status
echo ""
echo "=== Timer status ==="
systemctl status resumeai-report.timer --no-pager

echo ""
echo "=== Next run ==="
systemctl list-timers resumeai-report.timer --no-pager

echo ""
echo "=== Testing report RIGHT NOW ==="
systemctl start resumeai-report.service
sleep 5
tail -5 /opt/resumeaibot/logs/daily_report.log

echo ""
echo "✅ Done! Report will arrive every day at 08:00 MSK automatically."
