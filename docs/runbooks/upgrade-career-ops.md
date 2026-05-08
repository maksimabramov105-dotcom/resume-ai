# Runbook: Upgrade career-ops submodule pin

**Service:** career-ops quality engine  
**Submodule path:** `vendor/career-ops`  
**Upstream repo:** `https://github.com/santifer/career-ops`

---

## When to upgrade

- Upstream releases a new version with features you need (PDF template changes, new scoring modes, language packs)
- Security patches in Playwright or npm dependencies
- `npm audit` in the vendor dir returns high/critical CVEs

**When NOT to upgrade mid-sprint:** if a campaign is actively processing in `pending_review`, finish the review cycle first — the PDF paths stored in `autoapply.db` are absolute and tied to a particular generation run.

---

## Step 1 — Review the upstream changelog

```bash
cd vendor/career-ops
git fetch origin
git log --oneline HEAD..origin/main | head -30
```

Look for:
- Breaking changes to `generate-pdf.mjs` CLI interface
- Changes to `modes/oferta.md` scoring dimensions or weights (these are mirrored in `career_ops_adapter.py` — see Step 4)
- New npm deps that need `npm ci` re-run on the server

---

## Step 2 — Update the pin locally

```bash
# in repo root
cd vendor/career-ops
git checkout <new-sha>          # pin to a specific commit, never to a branch
cd ../..
git add vendor/career-ops
git diff --cached               # verify only the submodule pointer changed
```

---

## Step 3 — Rebuild node_modules in the submodule

```bash
cd vendor/career-ops
npm ci --omit=dev
cd ../..
```

If Playwright was updated (check `package.json` diff):

```bash
cd vendor/career-ops
npx playwright install chromium --with-deps
cd ../..
```

---

## Step 4 — Check scoring dimension parity

Open `vendor/career-ops/modes/oferta.md` and compare the scoring rubric against `autoapply/engines/career_ops_adapter.py` → `score_vacancy()`.

The adapter mirrors the 6-dimension weighting from oferta.md:

| Dimension | Weight in adapter |
|-----------|-------------------|
| skills_match | 0.30 |
| seniority_fit | 0.15 |
| location_remote | 0.15 |
| company_tier | 0.10 |
| salary_range | 0.20 |
| culture_mission | 0.10 |

If upstream changed weights or renamed dimensions, update `score_vacancy()` to match.

---

## Step 5 — Run the test suite

```bash
# from repo root
python -m pytest autoapply/tests/test_career_ops_adapter.py -v
```

All tests must pass before proceeding.

---

## Step 6 — Commit the pin bump

```bash
git commit -m "chore: bump career-ops submodule to <new-sha>

- <one-line summary of what changed upstream>
- Re-ran npm ci --omit=dev
- Scoring dimensions unchanged / updated (pick one)"
```

---

## Step 7 — Deploy to VPS

The submodule contents must be synced manually (VPS has no git):

```bash
VPS=root@72.56.250.53
DEST=/opt/resumeaibot

# Sync the submodule directory
rsync -av --delete \
  vendor/career-ops/ \
  $VPS:$DEST/vendor/career-ops/

# Re-install node deps on VPS
ssh $VPS "cd $DEST/vendor/career-ops && npm ci --omit=dev"

# If Playwright changed, reinstall chromium on VPS
ssh $VPS "cd $DEST/vendor/career-ops && npx playwright install chromium --with-deps"

# Sync the updated adapter
rsync -av autoapply/engines/career_ops_adapter.py \
  $VPS:$DEST/autoapply/engines/

# Restart the autoapply worker
ssh $VPS "systemctl restart autoapply-worker"

# Tail logs to confirm clean restart
ssh $VPS "journalctl -u autoapply-worker -f --lines=20"
```

---

## Step 8 — Smoke test

```bash
ssh $VPS "curl -fsS http://localhost:8080/api/health"
```

Then trigger one career-ops batch run in the dashboard (create a tiny test campaign with engine=career_ops, daily_limit=1) and confirm a `pending_review` row appears in the Applications tab.

---

## Rollback procedure

If the new version breaks something:

```bash
# locally
cd vendor/career-ops
git checkout 8e554cc4437c3a58e813378abb9b35e2e08a007e   # previous known-good pin
cd ../..
git add vendor/career-ops
git commit -m "revert: roll back career-ops to 8e554cc (stable)"

# re-sync to VPS (repeat Step 7 with the old sha checked out)
```

---

## Environment variables used by career-ops adapter

| Variable | Default | Purpose |
|----------|---------|---------|
| `CAREER_OPS_CV_DIR` | `/opt/resumeaibot/cv` | Directory where generated PDFs are stored |
| `CAREER_OPS_MIN_SCORE` | `5.5` | Minimum composite score (0–10) to trigger PDF generation |
| `CAREER_OPS_WORKDIR` | `/opt/careerops/workdir` | Scratch space for batch-runner.sh (sidecar mode only) |
| `OPENROUTER_API_KEY` | — | Used first for scoring (model: `anthropic/claude-haiku-3-5`) |
| `OPENAI_API_KEY` | — | Fallback if OpenRouter unavailable (model: `gpt-4o-mini`) |

---

## Notes on the sidecar service

`ops/systemd/career-ops.service` is an **optional** oneshot service for running the full `batch-runner.sh` flow (which invokes `claude -p` headless workers). The Python adapter in `career_ops_adapter.py` does **not** require the sidecar — it calls the scoring API and `generate-pdf.mjs` directly. The sidecar is only needed if you want to use the full career-ops CLI evaluation pipeline for batch processing.
