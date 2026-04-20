#!/usr/bin/env python3
"""
self_healer.py — Runs every 6 hours via systemd timer.
Checks all services, fixes common issues, reports to admin via Telegram.
"""
import asyncio
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
ADMIN_ID    = os.getenv("ADMIN_ID", "")
APP_DIR     = Path(os.getenv("APP_DIR", "/opt/resumeaibot"))
LOGS_DIR    = APP_DIR / "logs"
DB_AUTOAPPLY = APP_DIR / "autoapply" / "autoapply.db"
DB_BOT       = APP_DIR / "bot.db"

SERVICES = ["resumeaibot", "autoapply", "autoapply-worker"]

actions: list[str] = []


def _run(cmd: str) -> tuple[int, str]:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return result.returncode, (result.stdout + result.stderr).strip()


async def _telegram(text: str) -> None:
    if not BOT_TOKEN or not ADMIN_ID:
        print(text)
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={"chat_id": ADMIN_ID, "text": text, "parse_mode": "HTML"},
            )
    except Exception as e:
        print(f"[self_healer] telegram send failed: {e}")


# ── 1. Service health ─────────────────────────────────────────────────────────
def check_services() -> None:
    for svc in SERVICES:
        code, _ = _run(f"systemctl is-active {svc}")
        if code != 0:
            restart_code, _ = _run(f"systemctl restart {svc}")
            status = "restarted OK" if restart_code == 0 else "RESTART FAILED"
            actions.append(f"⚠️ {svc} was down — {status}")


# ── 2. Database integrity ─────────────────────────────────────────────────────
def check_db_integrity() -> None:
    for db in [DB_AUTOAPPLY, DB_BOT]:
        if not db.exists():
            continue
        code, out = _run(f'sqlite3 "{db}" "PRAGMA integrity_check;"')
        if code != 0 or "ok" not in out.lower():
            actions.append(f"❌ DB integrity FAILED: {db.name} — {out[:100]}")


# ── 3. Disk space ─────────────────────────────────────────────────────────────
def check_disk() -> None:
    total, used, free = shutil.disk_usage(APP_DIR)
    pct = int(used / total * 100)
    if pct > 80:
        # Clean old logs (keep last 7 days)
        cleaned_mb = 0
        if LOGS_DIR.exists():
            cutoff = time.time() - 7 * 86400
            for f in LOGS_DIR.glob("*.log.*"):
                if f.stat().st_mtime < cutoff:
                    cleaned_mb += f.stat().st_size // (1024 * 1024)
                    f.unlink()
        actions.append(f"⚠️ Disk at {pct}% — cleaned {cleaned_mb}MB old logs")


# ── 4. SSL certificate ────────────────────────────────────────────────────────
def check_ssl() -> None:
    code, out = _run(
        "openssl s_client -connect resumeai-bot.ru:443 -servername resumeai-bot.ru </dev/null 2>/dev/null | "
        "openssl x509 -noout -enddate 2>/dev/null"
    )
    if code != 0:
        return
    # e.g. notAfter=Apr 30 12:00:00 2025 GMT
    try:
        date_str = out.replace("notAfter=", "").strip()
        expiry = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
        days_left = (expiry - datetime.utcnow()).days
        if days_left < 7:
            _run("certbot renew --non-interactive --quiet")
            actions.append(f"⚠️ SSL expires in {days_left}d — ran certbot renew")
    except Exception:
        pass


# ── 5. API health ─────────────────────────────────────────────────────────────
async def check_api() -> None:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get("http://127.0.0.1:8080/api/health")
            if r.status_code != 200 or "ok" not in r.text:
                actions.append(f"❌ API /health returned {r.status_code}")
                _run("systemctl restart autoapply")
    except Exception as e:
        actions.append(f"❌ API unreachable: {str(e)[:80]} — restarting autoapply")
        _run("systemctl restart autoapply")


# ── 6. Memory usage ───────────────────────────────────────────────────────────
def check_memory() -> None:
    code, out = _run("ps -eo rss,comm | grep python | awk '{sum+=$1} END {print sum}'")
    if code == 0 and out.strip():
        rss_kb = int(out.strip() or "0")
        rss_mb = rss_kb // 1024
        if rss_mb > 500:
            for svc in SERVICES:
                _run(f"systemctl restart {svc}")
            actions.append(f"⚠️ Python RSS {rss_mb}MB > 500MB — restarted all services")


# ── 7. Log error rate ─────────────────────────────────────────────────────────
def check_log_errors() -> None:
    if not LOGS_DIR.exists():
        return
    error_count = 0
    error_types: dict[str, int] = {}
    cutoff_str = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d %H")
    for log_file in LOGS_DIR.glob("*.log"):
        try:
            for line in log_file.read_text(errors="ignore").splitlines():
                if "ERROR" in line and line[:13] >= cutoff_str[:13]:
                    error_count += 1
                    # Extract error type (word after ERROR)
                    parts = line.split("ERROR")
                    if len(parts) > 1:
                        word = parts[1].strip().split()[0] if parts[1].strip() else "unknown"
                        error_types[word] = error_types.get(word, 0) + 1
        except Exception:
            pass
    if error_count > 50:
        top = sorted(error_types.items(), key=lambda x: -x[1])[:5]
        top_str = ", ".join(f"{k}({v})" for k, v in top)
        actions.append(f"⚠️ {error_count} errors in last 6h — top: {top_str}")


# ── 8. Stale campaigns ────────────────────────────────────────────────────────
def check_stale_campaigns() -> None:
    if not DB_AUTOAPPLY.exists():
        return
    code, out = _run(
        f'sqlite3 "{DB_AUTOAPPLY}" '
        '"UPDATE campaigns SET status=\'paused\' WHERE status=\'running\' '
        "AND datetime(updated_at) < datetime('now','-24 hours') RETURNING id;\""
    )
    if code == 0 and out.strip():
        actions.append(f"⚠️ Reset {len(out.strip().splitlines())} stale campaigns")


# ── 9. Backup check ───────────────────────────────────────────────────────────
def check_backup() -> None:
    backup_dir = APP_DIR / "backups"
    if not backup_dir.exists():
        return
    backups = sorted(backup_dir.glob("*.db"), key=lambda f: f.stat().st_mtime)
    if not backups:
        return
    last_backup_age = time.time() - backups[-1].stat().st_mtime
    if last_backup_age > 86400:
        # Run backup script
        code, _ = _run(f"cd {APP_DIR} && python3 backup.py 2>/dev/null || bash scripts/backup_db.sh 2>/dev/null")
        actions.append("⚠️ No backup in 24h — ran backup now")


# ── Report ────────────────────────────────────────────────────────────────────
async def send_report() -> None:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    if not actions:
        summary = f"🔧 Self-Healer [{now}]\n✅ All systems healthy"
    else:
        lines = "\n".join(f"  {a}" for a in actions)
        summary = f"🔧 Self-Healer [{now}]\n{lines}"
    print(summary)
    await _telegram(summary)


async def main() -> None:
    print(f"[self_healer] starting at {datetime.utcnow().isoformat()}")
    check_services()
    check_db_integrity()
    check_disk()
    check_ssl()
    await check_api()
    check_memory()
    check_log_errors()
    check_stale_campaigns()
    check_backup()
    await send_report()


if __name__ == "__main__":
    asyncio.run(main())
