# Runbook: Restore Portfolio Data

**Symptom:** A user's public portfolio page (`resumeai-bot.ru/p/{handle}`) returns 404,
or the portfolio data is missing/corrupted after a DB incident.

**Affected tables:** `portfolios`, `portfolio_assets`, `portfolio_links`

---

## Quick triage

```bash
# 1. Check portfolio by handle
ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db \
  \"SELECT id, autoapply_user_id, handle, headline, updated_at
    FROM portfolios WHERE handle='USER_HANDLE'\""

# 2. Check portfolio by user email
ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db \
  \"SELECT p.id, p.handle, p.updated_at, u.email
    FROM portfolios p JOIN autoapply_users u ON u.id=p.autoapply_user_id
    WHERE u.email='user@example.com'\""

# 3. List all backups
ssh root@72.56.250.53 "ls -lht /opt/resumeaibot/backups/autoapply*.db | head -10"
```

---

## Step 1 — Find the last good backup

Backups are created twice daily by the backup cron (`scripts/backup_db.sh`).
Find the backup that still contains the portfolio:

```bash
# Replace HANDLE with the user's portfolio handle
for f in $(ls -t /opt/resumeaibot/backups/autoapply*.db); do
  count=$(sqlite3 "$f" "SELECT COUNT(*) FROM portfolios WHERE handle='HANDLE'" 2>/dev/null)
  echo "$f → $count rows"
  [ "$count" -gt 0 ] && break
done
```

Or run from local machine:
```bash
ssh root@72.56.250.53 "bash -c '
  for f in \$(ls -t /opt/resumeaibot/backups/autoapply*.db); do
    count=\$(sqlite3 \"\$f\" \"SELECT COUNT(*) FROM portfolios WHERE handle='"'"'HANDLE'"'"'\" 2>/dev/null)
    echo \"\$f → \$count\"
    [ \"\$count\" -gt \"0\" ] && break
  done'"
```

---

## Step 2 — Extract portfolio data from backup

```bash
BACKUP=/opt/resumeaibot/backups/autoapply.YYYY-MM-DD-HHMM.db
HANDLE=USER_HANDLE

# Get the portfolio row
ssh root@72.56.250.53 "sqlite3 -line $BACKUP \
  \"SELECT * FROM portfolios WHERE handle='$HANDLE'\""

# Get assets
ssh root@72.56.250.53 "sqlite3 -line $BACKUP \
  \"SELECT pa.* FROM portfolio_assets pa
    JOIN portfolios p ON p.id=pa.portfolio_id
    WHERE p.handle='$HANDLE'\""

# Get links
ssh root@72.56.250.53 "sqlite3 -line $BACKUP \
  \"SELECT pl.* FROM portfolio_links pl
    JOIN portfolios p ON p.id=pl.portfolio_id
    WHERE p.handle='$HANDLE'\""
```

---

## Step 3 — Restore specific portfolio rows

If the portfolio row exists in backup but is missing from live DB, restore it:

```bash
BACKUP=/opt/resumeaibot/backups/autoapply.YYYY-MM-DD-HHMM.db
LIVE=/opt/resumeaibot/autoapply.db

ssh root@72.56.250.53 "
  # Extract and re-insert portfolio (adjust column list if schema changed)
  sqlite3 $BACKUP \"
    ATTACH '$LIVE' AS live;
    INSERT OR REPLACE INTO live.portfolios
      SELECT * FROM portfolios WHERE handle='$HANDLE';
    INSERT OR REPLACE INTO live.portfolio_assets
      SELECT pa.* FROM portfolio_assets pa
      JOIN portfolios p ON p.id=pa.portfolio_id
      WHERE p.handle='$HANDLE';
    INSERT OR REPLACE INTO live.portfolio_links
      SELECT pl.* FROM portfolio_links pl
      JOIN portfolios p ON p.id=pl.portfolio_id
      WHERE p.handle='$HANDLE';
    DETACH live;
  \"
"
```

> **Warning:** `INSERT OR REPLACE` will overwrite any live row with the same primary key.
> If the user has made recent edits to a partially-intact portfolio, export the live row
> first before overwriting.

---

## Step 4 — Verify the restore

```bash
# Check row is back
ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db \
  \"SELECT id, handle, headline, updated_at FROM portfolios WHERE handle='$HANDLE'\""

# Verify the public page responds
curl -s -o /dev/null -w "%{http_code}" https://resumeai-bot.ru/p/$HANDLE
```

---

## Full database restore (last resort)

If the entire DB needs to be restored (not just one portfolio):

```bash
# See docs/runbooks/restore-db.md
```

> The autoapply.db and bot.db are backed up independently.
> Restoring autoapply.db does NOT affect bot.db (Telegram bot users/credits).

---

## Upload assets restored from local files

If a user reports their portfolio photo is missing but the row exists:

1. The image URL stored in `portfolio_assets.url` is relative (e.g. `/uploads/...`)
2. Check if the file exists on VPS:
   ```bash
   ssh root@72.56.250.53 "ls /opt/resumeaibot/uploads/ | grep USER_ID"
   ```
3. If missing, ask the user to re-upload via `resumeai-bot.ru/app/profile/portfolio`

---

## Prevention

- Backups run at 00:00, 06:00, 12:00, 18:00 UTC via `health-check.timer`
- Retention: last 7 days × 4/day = ~28 files
- Each backup is a full SQLite copy (`cp` — not incremental)
- To verify backup health: `sqlite3 BACKUP_FILE "PRAGMA integrity_check"`
