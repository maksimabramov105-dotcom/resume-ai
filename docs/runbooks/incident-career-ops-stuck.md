# Runbook: career-ops HITL Queue Stuck

**Symptom:** Applications accumulate in `status='pending_review'` but users cannot
submit them, OR the career-ops worker is not scoring/queuing new vacancies.

**Service:** `autoapply.service` (port 8080) · `autoapply-worker.service`

---

## Quick triage

```bash
# 1. How many pending_review apps exist?
ssh root@72.56.250.53 \
  "sqlite3 /opt/resumeaibot/autoapply.db \
   \"SELECT COUNT(*), MIN(sent_at) FROM applications WHERE status='pending_review'\""

# 2. Is the worker running?
ssh root@72.56.250.53 "systemctl is-active autoapply-worker"

# 3. Last 30 lines of worker log
ssh root@72.56.250.53 "journalctl -u autoapply-worker -n 30 --no-pager"

# 4. Is the API accepting review actions?
curl -s https://resumeai-bot.ru/api/health/deep | python3 -m json.tool
```

---

## Scenario A — Worker not creating pending_review entries

**Cause:** career-ops scoring is failing (OpenRouter/OpenAI unreachable, or score
always < MIN_SCORE threshold).

**Steps:**

1. Check API key availability:
   ```bash
   ssh root@72.56.250.53 "grep -E 'OPENROUTER|OPENAI' /opt/resumeaibot/.env | head -4"
   ```

2. Test scoring manually:
   ```bash
   ssh root@72.56.250.53 "cd /opt/resumeaibot && .venv/bin/python3 -c \"
   import asyncio, os
   os.chdir('/opt/resumeaibot')
   import sys; sys.path.insert(0,'bot'); sys.path.insert(0,'.')
   from autoapply.engines.career_ops_adapter import score_vacancy
   vac = {'title':'Backend Engineer','description':'Python FastAPI 3+ yrs','company':'Acme'}
   user = {'resume_text':'5 years Python FastAPI','plan':'pro'}
   result = asyncio.run(score_vacancy(vac, user))
   print(result)
   \""
   ```

3. If scoring returns `None` or `composite_score=0`:
   - Check `OPENROUTER_API_KEY` is set and has credits
   - Fallback: set `CAREER_OPS_MIN_SCORE=0` temporarily to bypass the score gate

4. Check Node.js is available for PDF generation:
   ```bash
   ssh root@72.56.250.53 "which node && node --version"
   ```
   If node is missing: PDF generation is skipped (applications still queue without PDF — this is expected behavior, not a blocker).

---

## Scenario B — pending_review entries exist but HITL submit fails

**Cause:** `POST /api/applications/{id}/review` returns 4xx/5xx.

**Steps:**

1. Reproduce the error:
   ```bash
   # Replace TOKEN and APP_ID with real values
   curl -X POST https://resumeai-bot.ru/api/applications/APP_ID/review \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"action":"submit"}' -v
   ```

2. If 404 — application ID doesn't exist or belongs to a different user. Check DB:
   ```bash
   ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db \
     \"SELECT id, user_id, status, engine FROM applications WHERE id=APP_ID\""
   ```

3. If 500 — check API logs:
   ```bash
   ssh root@72.56.250.53 "journalctl -u autoapply -n 50 --no-pager | grep -i 'error\|exception'"
   ```

4. If `ATSFiller.apply()` fails (ATS form not found):
   - The vacancy URL may have expired. Manually set status to `sent`:
   ```bash
   ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db \
     \"UPDATE applications SET status='sent', last_user_action_at=datetime('now') WHERE id=APP_ID\""
   ```

---

## Scenario C — Bulk clear stale pending_review queue

If a large number of pending_review entries are older than N days and should be discarded:

```bash
# DRY RUN first — check count
ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db \
  \"SELECT COUNT(*) FROM applications
    WHERE status='pending_review'
    AND sent_at < datetime('now','-7 days')\""

# APPLY after confirming count is expected
ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db \
  \"UPDATE applications
    SET status='rejected', last_user_action_at=datetime('now')
    WHERE status='pending_review'
    AND sent_at < datetime('now','-7 days')\""
```

---

## Scenario D — Restart career-ops worker

```bash
ssh root@72.56.250.53 "systemctl restart autoapply-worker && sleep 5 && systemctl status autoapply-worker --no-pager -n 10"
```

If the worker fails to restart, check for a stale lock:
```bash
ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db \
  \"SELECT * FROM worker_lock\""

# Clear stale lock if present
ssh root@72.56.250.53 "sqlite3 /opt/resumeaibot/autoapply.db \
  \"DELETE FROM worker_lock\""
```

---

## Environment variables affecting career-ops

| Variable | Default | Effect |
|----------|---------|--------|
| `CAREER_OPS_MIN_SCORE` | `5.5` | Minimum composite score (0–10) to queue a vacancy |
| `CAREER_OPS_CV_DIR` | `/opt/resumeaibot/cv` | Where PDFs are written |
| `CAREER_OPS_WORKDIR` | (vendor dir) | career-ops Node working directory |
| `OPENROUTER_API_KEY` | — | Primary scoring API (claude-haiku-3-5) |
| `OPENAI_API_KEY` | — | Fallback scoring API (gpt-4o-mini) |

See also: [upgrade-career-ops.md](upgrade-career-ops.md)
