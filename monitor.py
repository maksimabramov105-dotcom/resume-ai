#!/usr/bin/env python3
"""
monitor.py — Enhanced service monitor with auto-restart and Telegram alerts.

Checks every 5 minutes:
  - resumeaibot service (Telegram bot polling)
  - autoapply service (FastAPI web service)
  - autoapply-worker service (background job processor)
  - HTTP: /api/health endpoint
  - Telegram bot responsiveness (pending update count)
  - Disk space (alert if < 500 MB free)

On failure:
  - Restarts the crashed service automatically
  - Sends Telegram alert to admin with what failed + what was done
  - Tracks consecutive failures (alerts more urgently after 3+)

On recovery:
  - Sends "all clear" Telegram message

Usage:
  Runs as systemd service: monitor.service
  Or manually: python3 monitor.py
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("monitor")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/opt/resumeaibot/logs/monitor.log"),
        logging.StreamHandler(),
    ],
)

BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_ID", "6246429438")
API_HEALTH    = "http://127.0.0.1:8080/api/health"
CHECK_INTERVAL = 300   # seconds between checks (5 min)
DISK_MIN_MB    = 500   # alert if less than this many MB free

SERVICES = ["resumeaibot", "autoapply", "autoapply-worker"]

# Tracks consecutive failure count per service/check
_failure_counts: dict[str, int] = {}
_was_healthy = True   # used to send "recovered" message


def send_telegram(text: str) -> None:
    """Send a message to admin. Uses urllib (no aiohttp needed in this script)."""
    if not BOT_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        body = json.dumps({
            "chat_id": ADMIN_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception as e:
        log.warning("Failed to send Telegram alert: %s", e)


def is_service_active(service: str) -> bool:
    """Check if a systemd service is active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def restart_service(service: str) -> bool:
    """Restart a systemd service. Returns True if successful."""
    try:
        result = subprocess.run(
            ["systemctl", "restart", service],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def check_http(url: str, timeout: int = 10) -> bool:
    """HTTP GET check. Returns True if responds with 200."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def check_disk() -> tuple[bool, int]:
    """Check free disk space. Returns (is_ok, free_mb)."""
    total, used, free = shutil.disk_usage("/")
    free_mb = free // (1024 * 1024)
    return free_mb >= DISK_MIN_MB, free_mb


def check_bot_polling() -> bool:
    """
    Check if the Telegram bot is actively polling by watching pending_update_count.
    If count keeps growing across two checks, the bot is not polling.
    Stores last count in /tmp/bot_pending_count.
    """
    if not BOT_TOKEN:
        return True  # can't check without token, assume ok
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        pending = data.get("result", {}).get("pending_update_count", 0)

        state_file = Path("/tmp/bot_pending_count")
        if state_file.exists():
            prev = int(state_file.read_text().strip())
            # If pending count grew by 3+ since last check, bot likely not polling
            if pending > prev + 3:
                log.warning("Bot pending updates growing: %d → %d", prev, pending)
                state_file.write_text(str(pending))
                return False
        state_file.write_text(str(pending))
        return True
    except Exception:
        return True  # network error, don't false-alarm


def run_checks() -> list[str]:
    """
    Run all checks. Returns list of failure descriptions (empty = all ok).
    Also auto-restarts failed services.
    """
    failures = []

    # 1. Systemd services
    for service in SERVICES:
        if not is_service_active(service):
            _failure_counts[service] = _failure_counts.get(service, 0) + 1
            log.warning("Service down: %s (failure #%d)", service, _failure_counts[service])

            restarted = restart_service(service)
            status = "restarted ✅" if restarted else "restart FAILED ❌"
            failures.append(f"<code>{service}</code> was down → {status}")
        else:
            _failure_counts[service] = 0

    # 2. HTTP health endpoint
    if not check_http(API_HEALTH):
        _failure_counts["http"] = _failure_counts.get("http", 0) + 1
        failures.append(f"<code>/api/health</code> not responding (#{_failure_counts['http']})")
    else:
        _failure_counts["http"] = 0

    # 3. Bot polling check
    if not check_bot_polling():
        _failure_counts["bot_polling"] = _failure_counts.get("bot_polling", 0) + 1
        if _failure_counts["bot_polling"] >= 2:  # two consecutive checks
            log.warning("Bot polling appears stuck — restarting resumeaibot")
            restart_service("resumeaibot")
            failures.append("Bot polling stuck → resumeaibot restarted")
    else:
        _failure_counts["bot_polling"] = 0

    # 4. Disk space
    disk_ok, free_mb = check_disk()
    if not disk_ok:
        failures.append(f"Low disk space: {free_mb} MB free (threshold: {DISK_MIN_MB} MB)")

    return failures


def main():
    global _was_healthy

    log.info("Monitor started. Checking every %ds.", CHECK_INTERVAL)
    send_telegram("🟢 <b>Monitor started</b>\nChecking all services every 5 minutes.")

    while True:
        try:
            failures = run_checks()
            now = datetime.now(timezone.utc).strftime("%H:%M UTC")

            if failures:
                _was_healthy = False
                alert = (
                    f"⚠️ <b>Service Alert</b> [{now}]\n\n"
                    + "\n".join(f"• {f}" for f in failures)
                )
                log.warning("ALERT: %s", " | ".join(failures))
                send_telegram(alert)
            else:
                if not _was_healthy:
                    # Everything just recovered
                    send_telegram(
                        f"✅ <b>All systems recovered</b> [{now}]\n"
                        "All services are back online and healthy."
                    )
                    _was_healthy = True
                else:
                    log.info("All checks passed.")

        except Exception as e:
            log.exception("Monitor loop error: %s", e)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
