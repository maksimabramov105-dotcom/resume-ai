#!/usr/bin/env python3
"""
backup.py — Automatic daily database backup to Telegram.

Backs up bot.db and autoapply.db by sending them as files to the admin chat.
Also saves a local copy to /opt/resumeaibot/backups/ (keeps last 7).

Runs as a scheduled job inside run.py (3:00 AM UTC daily).
Can also be run standalone: python3 backup.py

Why Telegram? Free, instant, no S3/FTP setup needed. Files up to 50MB are fine.
"""
import asyncio
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

log = logging.getLogger(__name__)

BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_ID", "0")))
BOT_DB        = os.getenv("BOT_DB",       "/opt/resumeaibot/bot.db")
AUTOAPPLY_DB  = os.getenv("AUTOAPPLY_DB", "/opt/resumeaibot/autoapply.db")
BACKUP_DIR    = Path(os.getenv("BACKUP_DIR", "/opt/resumeaibot/backups"))
KEEP_BACKUPS  = 7   # keep last N daily backups locally


def _local_backup(src: str, stamp: str) -> Path | None:
    """Copy a DB file to the local backup dir with a timestamp suffix."""
    src_path = Path(src)
    if not src_path.exists():
        log.warning("DB not found, skipping local backup: %s", src)
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"{src_path.stem}_{stamp}.db"
    shutil.copy2(src, dest)
    log.info("Local backup: %s → %s", src, dest)
    return dest


def _prune_old_backups(stem: str) -> None:
    """Keep only the most recent KEEP_BACKUPS files matching stem_*.db."""
    files = sorted(BACKUP_DIR.glob(f"{stem}_*.db"), key=lambda f: f.name)
    for old in files[:-KEEP_BACKUPS]:
        old.unlink()
        log.info("Pruned old backup: %s", old)


async def _send_file_to_telegram(file_path: Path, caption: str) -> bool:
    """Upload a file to admin chat via Telegram Bot API. Returns True on success."""
    if not BOT_TOKEN:
        log.warning("BOT_TOKEN not set — cannot send backup")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as f:
                form = aiohttp.FormData()
                form.add_field("chat_id", str(ADMIN_CHAT_ID))
                form.add_field("caption", caption)
                form.add_field(
                    "document",
                    f,
                    filename=file_path.name,
                    content_type="application/octet-stream",
                )
                async with session.post(url, data=form, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    result = await resp.json()
                    if result.get("ok"):
                        log.info("Backup sent to Telegram: %s", file_path.name)
                        return True
                    else:
                        log.error("Telegram upload failed: %s", result)
                        return False
    except Exception as e:
        log.exception("Failed to send backup to Telegram: %s", e)
        return False


async def run_backup() -> None:
    """
    Main backup routine:
    1. Create timestamped local copies of both DBs
    2. Send them to admin Telegram chat
    3. Prune old local backups
    4. Send summary message
    """
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log.info("Starting daily backup (stamp=%s)…", stamp)

    results = []

    for db_path in [BOT_DB, AUTOAPPLY_DB]:
        local_copy = _local_backup(db_path, stamp)
        if local_copy is None:
            results.append(f"⚠️ {Path(db_path).name} — not found")
            continue

        file_size_kb = local_copy.stat().st_size // 1024
        caption = (
            f"💾 <b>Daily Backup</b>\n"
            f"File: {local_copy.name}\n"
            f"Size: {file_size_kb} KB\n"
            f"Date: {stamp} UTC"
        )
        ok = await _send_file_to_telegram(local_copy, caption)
        status = "✅" if ok else "⚠️ local only"
        results.append(f"{status} {local_copy.name} ({file_size_kb} KB)")

        # Prune old local backups for this DB
        _prune_old_backups(Path(db_path).stem)

    # Send summary to admin
    summary = "\n".join(results)
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": ADMIN_CHAT_ID,
                    "text": f"💾 <b>Backup complete</b>\n{summary}",
                    "parse_mode": "HTML",
                },
                timeout=aiohttp.ClientTimeout(total=10),
            )
    except Exception:
        pass

    log.info("Backup complete: %s", summary)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(run_backup())
