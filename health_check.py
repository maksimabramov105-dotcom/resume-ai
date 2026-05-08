#!/usr/bin/env python3
"""
health_check.py — System health monitor
Runs every 5 minutes via systemd timer.
Checks all services and sends Telegram alerts on failure.
"""
import asyncio
import aiohttp
import aiosqlite
import email.mime.multipart
import email.mime.text
import logging
import os
import smtplib
import sys
import shutil
import subprocess
from datetime import datetime

ADMIN_CHAT_ID = int(os.getenv("ADMIN_ID", "0"))
BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
BOT_DB        = os.getenv("BOT_DB", "/opt/resumeaibot/bot.db")
AUTOAPPLY_DB  = os.getenv("AUTOAPPLY_DB", "/opt/resumeaibot/autoapply.db")
LOGS_DIR      = os.getenv("LOGS_DIR", "/opt/resumeaibot/logs")

# Admin email for critical alerts (service down, disk full, credits exhausted)
ADMIN_EMAIL   = os.getenv("ADMIN_EMAIL", "max737books@gmail.com")
SMTP_HOST     = os.getenv("SMTP_HOST", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM     = os.getenv("SMTP_FROM", SMTP_USER)

# Failures that warrant an email (not just Telegram) — service names
CRITICAL_CHECKS = {"bot_service", "autoapply_api", "worker", "disk_space"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger("health_check")


async def check_bot_db() -> tuple[bool, str]:
    """Check bot SQLite database connectivity."""
    try:
        async with aiosqlite.connect(BOT_DB, timeout=5) as db:
            async with db.execute("SELECT 1") as cur:
                row = await cur.fetchone()
                if row and row[0] == 1:
                    return True, "bot.db OK"
        return False, "bot.db: SELECT 1 returned no result"
    except Exception as e:
        return False, f"bot.db error: {e}"


async def check_autoapply_db() -> tuple[bool, str]:
    """Check autoapply SQLite database connectivity."""
    try:
        async with aiosqlite.connect(AUTOAPPLY_DB, timeout=5) as db:
            async with db.execute("SELECT 1") as cur:
                row = await cur.fetchone()
                if row and row[0] == 1:
                    return True, "autoapply.db OK"
        return False, "autoapply.db: SELECT 1 returned no result"
    except Exception as e:
        return False, f"autoapply.db error: {e}"


async def check_autoapply_api() -> tuple[bool, str]:
    """Check AutoApply FastAPI service health endpoint."""
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("http://localhost:8080/api/health") as resp:
                if resp.status == 200:
                    return True, f"autoapply API OK (HTTP {resp.status})"
                return False, f"autoapply API returned HTTP {resp.status}"
    except asyncio.TimeoutError:
        return False, "autoapply API timeout (>5s)"
    except Exception as e:
        return False, f"autoapply API unreachable: {e}"


async def check_arbeitnow_api() -> tuple[bool, str]:
    """Check Arbeitnow job board API availability."""
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("https://www.arbeitnow.com/api/job-board-api?page=1", timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    count = len(data.get("data", []))
                    return True, f"Arbeitnow API OK (jobs={count})"
                return False, f"Arbeitnow API returned HTTP {resp.status}"
    except asyncio.TimeoutError:
        return False, "Arbeitnow API timeout (>10s)"
    except Exception as e:
        return False, f"Arbeitnow API error: {e}"


async def check_bot_service() -> tuple[bool, str]:
    """Check resumeaibot systemd service status."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "resumeaibot"],
            capture_output=True, text=True, timeout=5
        )
        status = result.stdout.strip()
        if status == "active":
            return True, "resumeaibot service active"
        return False, f"resumeaibot service status: {status}"
    except subprocess.TimeoutExpired:
        return False, "systemctl check timed out"
    except FileNotFoundError:
        return False, "systemctl not found (not a systemd system?)"
    except Exception as e:
        return False, f"resumeaibot service check error: {e}"


async def check_dashboard() -> tuple[bool, str]:
    """Check AutoApply dashboard (Next.js SPA served by FastAPI on :8080).

    Architecture (post-Streamlit pivot): nginx proxies /app → FastAPI :8080.
    We verify two things:
      1. nginx is running (systemd)
      2. FastAPI serves the /app/ SPA entry point (HTTP 200)
    """
    # 1. nginx systemd check
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "nginx"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip() != "active":
            return False, f"nginx service status: {result.stdout.strip()}"
    except Exception as e:
        return False, f"nginx service check error: {e}"

    # 2. FastAPI /app/ endpoint check
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("http://localhost:8080/app/") as resp:
                if resp.status in (200, 304):
                    return True, f"dashboard OK (nginx active, /app/ HTTP {resp.status})"
                return False, f"dashboard: FastAPI /app/ returned HTTP {resp.status}"
    except asyncio.TimeoutError:
        return False, "dashboard: FastAPI /app/ timeout (>5s)"
    except Exception as e:
        return False, f"dashboard: FastAPI /app/ error: {e}"


async def check_disk_space() -> tuple[bool, str]:
    """Check available disk space (fail if < 1 GB free)."""
    try:
        usage = shutil.disk_usage("/")
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        used_pct = (usage.used / usage.total) * 100
        if free_gb >= 1.0:
            return True, f"disk OK: {free_gb:.1f}GB free ({used_pct:.0f}% used)"
        return False, f"disk CRITICAL: only {free_gb:.2f}GB free of {total_gb:.1f}GB ({used_pct:.0f}% used)"
    except Exception as e:
        return False, f"disk check error: {e}"


async def check_worker() -> tuple[bool, str]:
    """Check autoapply-worker systemd service status."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "autoapply-worker"],
            capture_output=True, text=True, timeout=5
        )
        status = result.stdout.strip()
        if status == "active":
            return True, "autoapply-worker service active"
        return False, f"autoapply-worker service status: {status}"
    except subprocess.TimeoutExpired:
        return False, "systemctl check timed out"
    except FileNotFoundError:
        return False, "systemctl not found (not a systemd system?)"
    except Exception as e:
        return False, f"autoapply-worker check error: {e}"


def _restart_service(service_name: str) -> bool:
    """Attempt to restart a systemd service. Returns True if successful."""
    try:
        result = subprocess.run(
            ["systemctl", "restart", service_name],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


async def send_alert(message: str) -> None:
    """Send a Telegram alert message to the admin."""
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN not set — cannot send Telegram alert")
        log.warning("ALERT: %s", message)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ADMIN_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    log.info("Telegram alert sent successfully")
                else:
                    body = await resp.text()
                    log.error("Telegram alert failed: HTTP %d — %s", resp.status, body)
    except Exception as e:
        log.error("Failed to send Telegram alert: %s", e)


def send_critical_email(subject: str, body: str) -> None:
    """Send an email to the admin for critical (unrecovered) failures.
    Only fires when SMTP credentials are configured and ADMIN_EMAIL is set.
    Runs synchronously — call from asyncio via run_in_executor if needed.
    """
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD or not ADMIN_EMAIL:
        log.warning("SMTP not configured — critical email skipped (check SMTP_* env vars)")
        return
    try:
        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"ResumeAI Monitor <{SMTP_FROM or SMTP_USER}>"
        msg["To"] = ADMIN_EMAIL
        msg.attach(email.mime.text.MIMEText(body, "plain", "utf-8"))

        if SMTP_PORT == 465:
            ctx = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15)
        else:
            ctx = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
            ctx.starttls()
        with ctx as smtp:
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.sendmail(SMTP_FROM or SMTP_USER, ADMIN_EMAIL, msg.as_bytes())
        log.info("Critical email sent to %s — %s", ADMIN_EMAIL, subject)
    except Exception as e:
        log.error("Failed to send critical email: %s", e)


async def attempt_restart_and_recheck(
    service_name: str,
    recheck_fn,
    failure_label: str,
) -> tuple[bool, str]:
    """Restart a service, wait 30s, recheck. Returns (recovered, status_msg)."""
    log.info("Attempting restart of %s...", service_name)
    ok = _restart_service(service_name)
    if not ok:
        return False, f"{failure_label}: restart command failed"

    log.info("Waiting 30s for %s to come back...", service_name)
    await asyncio.sleep(30)

    still_ok, msg = await recheck_fn()
    if still_ok:
        log.info("%s recovered after restart", service_name)
        return True, f"{failure_label}: recovered after restart"
    return False, f"{failure_label}: still down after restart — {msg}"


STATE_FILE = os.path.join(os.getenv("LOGS_DIR", "/opt/resumeaibot/logs"), ".health_state")


def _read_state() -> set[str]:
    """Return set of check names that were failing in the previous run."""
    try:
        data = open(STATE_FILE).read().strip()
        return set(data.split(",")) if data else set()
    except FileNotFoundError:
        return set()
    except Exception:
        return set()


def _write_state(failing: set[str]) -> None:
    """Persist current failing check names to disk."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        open(STATE_FILE, "w").write(",".join(sorted(failing)))
    except Exception as e:
        log.warning("Could not write state file: %s", e)


async def main() -> None:
    log.info("=== Health check started at %s ===", datetime.now().isoformat())

    # Critical checks: failure triggers Telegram + email alerts
    checks = [
        ("bot_db",        check_bot_db),
        ("autoapply_db",  check_autoapply_db),
        ("autoapply_api", check_autoapply_api),
        ("bot_service",   check_bot_service),
        ("dashboard",     check_dashboard),
        ("disk_space",    check_disk_space),
        ("worker",        check_worker),
    ]

    # Informational checks: logged but never trigger alerts
    # (external APIs outside our control — their downtime ≠ our failure)
    info_checks = [
        ("arbeitnow_api", check_arbeitnow_api),
    ]

    # Run all checks concurrently
    all_fns = [fn() for _, fn in checks] + [fn() for _, fn in info_checks]
    all_names = [name for name, _ in checks] + [name for name, _ in info_checks]
    results_raw = await asyncio.gather(*all_fns, return_exceptions=True)

    results: dict[str, tuple[bool, str]] = {}
    for name, raw in zip(all_names, results_raw):
        if isinstance(raw, Exception):
            results[name] = (False, f"Unexpected exception: {raw}")
        else:
            results[name] = raw
        ok, msg = results[name]
        level = log.info if ok else log.warning
        level("[%s] %s", name, msg)

    # Only critical checks count as failures worth alerting on
    failures = {name: msg for name, (ok, msg) in results.items()
                if not ok and name not in {n for n, _ in info_checks}}

    prev_failing = _read_state()

    if not failures:
        log.info("All checks passed — system healthy.")
        if prev_failing:
            # Was failing before → send recovery notification
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            recovered_names = ", ".join(f"<code>{n}</code>" for n in sorted(prev_failing))
            msg = (
                f"✅ <b>All systems recovered</b>\n"
                f"🕐 {ts}\n\n"
                f"Previously failing: {recovered_names}\n"
                f"Status: all checks passing ✓"
            )
            await send_alert(msg)
            log.info("Recovery notification sent (was failing: %s)", prev_failing)
        _write_state(set())
        return

    # --- Auto-restart logic ---
    restart_reports: list[str] = []

    if "bot_service" in failures:
        recovered, rpt = await attempt_restart_and_recheck(
            "resumeaibot", check_bot_service, "Bot service"
        )
        restart_reports.append(rpt)
        if recovered:
            del failures["bot_service"]

    if "autoapply_api" in failures:
        recovered, rpt = await attempt_restart_and_recheck(
            "autoapply", check_autoapply_api, "AutoApply API"
        )
        restart_reports.append(rpt)
        if recovered:
            del failures["autoapply_api"]

    if "worker" in failures:
        recovered, rpt = await attempt_restart_and_recheck(
            "autoapply-worker", check_worker, "AutoApply Worker"
        )
        restart_reports.append(rpt)
        if recovered:
            del failures["worker"]

    if "dashboard" in failures:
        # Dashboard = nginx + FastAPI /app/.  Try restarting nginx first,
        # then autoapply if that doesn't help.
        recovered, rpt = await attempt_restart_and_recheck(
            "nginx", check_dashboard, "nginx (dashboard)"
        )
        restart_reports.append(rpt)
        if recovered:
            del failures["dashboard"]
        else:
            # nginx came back but /app/ still fails → autoapply is the issue
            recovered2, rpt2 = await attempt_restart_and_recheck(
                "autoapply", check_dashboard, "AutoApply (dashboard fallback)"
            )
            restart_reports.append(rpt2)
            if recovered2:
                del failures["dashboard"]

    # Build alert message
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"🚨 <b>Health Check Alert</b>"]
    lines.append(f"🕐 {ts}")
    lines.append("")

    if failures:
        lines.append(f"❌ <b>Still failing ({len(failures)}):</b>")
        for name, msg in failures.items():
            lines.append(f"  • <code>{name}</code>: {msg}")
    else:
        lines.append("✅ All issues resolved via auto-restart")

    if restart_reports:
        lines.append("")
        lines.append("🔄 <b>Restart attempts:</b>")
        for rpt in restart_reports:
            lines.append(f"  • {rpt}")

    alert_text = "\n".join(lines)
    log.warning("Sending alert:\n%s", alert_text)
    await send_alert(alert_text)

    # Persist which checks are still failing so next run can detect recovery
    _write_state(set(failures.keys()))

    # Send email ONLY for critical unrecovered failures (service down, disk full)
    critical_failures = {k: v for k, v in failures.items() if k in CRITICAL_CHECKS}
    if critical_failures:
        email_lines = [
            "ResumeAI critical alert — action required.",
            f"Time: {ts}",
            "",
            "Critical failures:",
        ]
        for name, msg_txt in critical_failures.items():
            email_lines.append(f"  • {name}: {msg_txt}")
        if restart_reports:
            email_lines.append("")
            email_lines.append("Auto-restart attempts:")
            for rpt in restart_reports:
                email_lines.append(f"  • {rpt}")
        email_lines += [
            "",
            "Server: 72.56.250.53",
            "Check: ssh root@72.56.250.53",
        ]
        loop = asyncio.get_event_loop()
        subject = f"[ResumeAI] CRITICAL: {', '.join(critical_failures.keys())} down"
        await loop.run_in_executor(
            None, send_critical_email, subject, "\n".join(email_lines)
        )

    # Exit with error code so systemd timer can track failures
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
