"""
auto_test.py — Automated health checks for resumeai-bot.ru
Runs every 6 hours via cron. Sends Telegram alert on failure.

Crontab entry:
  0 */6 * * * cd /opt/resumeaibot && .venv/bin/python3 auto_test.py >> /var/log/resumeai_health.log 2>&1
"""
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")
BASE_URL     = "https://resumeai-bot.ru"
LOG_FILE     = "/var/log/resumeai_health.log"
STATE_FILE   = "/tmp/resumeai_health_state.json"  # tracks consecutive failures

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("auto_test")

TESTS = [
    # (path, method, expected_status, description, critical)
    ("/",                                          "GET", 200, "Homepage",            True),
    ("/app",                                       "GET", 200, "App dashboard",       True),
    ("/api/health",                                "GET", 200, "API health",          True),
    ("/sitemap.xml",                               "GET", 200, "Sitemap",             False),
    ("/robots.txt",                                "GET", 200, "Robots",              False),
    ("/blog/",                                     "GET", 200, "Blog index",          False),
    ("/blog/rss.xml",                              "GET", 200, "RSS feed",            False),
    ("/privacy.html",                              "GET", 200, "Privacy",             False),
    ("/api/stats",                                 "GET", 200, "Stats API",           True),
    ("/api/resume/templates",                      "GET", 200, "Templates API",       False),
    ("/google1f1e304f8ad3e56e.html",              "GET", 200, "Google verification", False),
    ("/yandex_300171d04809e29f.html",             "GET", 200, "Yandex verification", False),
]


def check(path: str, method: str, expected: int) -> tuple[bool, int, float]:
    """Returns (ok, status_code, response_time_ms)."""
    url = BASE_URL + path
    t0 = time.time()
    try:
        req = urllib.request.Request(url, method=method)
        req.add_header("User-Agent", "ResumeAI-HealthBot/1.0")
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        logger.error("  ERROR %s: %s", path, e)
        return False, 0, (time.time() - t0) * 1000
    elapsed = (time.time() - t0) * 1000
    return status == expected, status, elapsed


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def send_telegram(message: str) -> None:
    if not BOT_TOKEN or not ADMIN_CHAT_ID:
        logger.warning("No Telegram config — cannot send alert")
        return
    payload = json.dumps({"chat_id": ADMIN_CHAT_ID, "text": message}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        logger.info("Telegram alert sent")
    except Exception as e:
        logger.error("Failed to send Telegram alert: %s", e)


def attempt_autorestart(service: str = "autoapply") -> bool:
    """Attempt to restart a systemd service."""
    try:
        import subprocess
        result = subprocess.run(
            ["systemctl", "restart", service],
            capture_output=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        logger.error("Auto-restart failed: %s", e)
        return False


def main():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=== Health check started at %s ===", now)

    state = load_state()
    results = []
    failures = []
    critical_failures = []

    for path, method, expected, desc, critical in TESTS:
        ok, status, elapsed = check(path, method, expected)
        icon = "✅" if ok else "❌"
        logger.info("  %s %s → %s (%dms)", icon, desc, status or "ERR", int(elapsed))
        results.append((desc, ok, status, int(elapsed)))
        if not ok:
            failures.append((desc, path, status, critical))
            if critical:
                critical_failures.append((desc, path, status))

    # Track consecutive failures per path
    for desc, path, status, critical in failures:
        key = path
        state[key] = state.get(key, 0) + 1
    # Reset passing tests
    for path, method, expected, desc, critical in TESTS:
        if not any(f[1] == path for f in failures):
            state.pop(path, None)

    save_state(state)

    if not failures:
        logger.info("=== All %d checks passed ===", len(TESTS))
        return

    # Build alert message
    fail_lines = "\n".join(
        f"{'🔴' if c else '🟡'} {d}: {s or 'timeout'}"
        for d, p, s, c in failures
    )
    alert = (
        f"⚠️ ResumeAI Health Alert — {now}\n\n"
        f"Failed {len(failures)}/{len(TESTS)} checks:\n"
        f"{fail_lines}\n\n"
        f"Site: {BASE_URL}"
    )
    send_telegram(alert)

    # Auto-restart if critical endpoints have failed 3+ consecutive times
    for desc, path, status, critical in critical_failures:
        consecutive = state.get(path, 0)
        if critical and consecutive >= 3:
            logger.warning("CRITICAL: %s failed %d times — attempting auto-restart", path, consecutive)
            restarted = attempt_autorestart("autoapply")
            msg = f"🔄 Auto-restarted autoapply service ({'success' if restarted else 'FAILED'}) after {consecutive} consecutive failures on {path}"
            logger.info(msg)
            send_telegram(msg)

    logger.info("=== Health check complete: %d failures ===", len(failures))
    sys.exit(1 if critical_failures else 0)


if __name__ == "__main__":
    main()
