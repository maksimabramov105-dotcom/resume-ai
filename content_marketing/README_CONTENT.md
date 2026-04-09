# Content Marketing System — РезюмеАИ

Fully automated content distribution across Reddit, Telegra.ph, and VK.
Generates AI content with Claude, publishes on a weekly schedule.

---

## Architecture

```
content_generator.py  ← runs Monday, generates 5 formats per topic
        ↓
content_output/
  2026-01-06_kak-napisat-rezyume/
    reddit.txt
    twitter_thread.txt
    telegraph_article.txt
    vk_post.txt
    quora_answer.txt
    meta.json
        ↓
reddit_poster.py       ← runs Tuesday + Friday
telegraph_publisher.py ← runs Wednesday + Saturday
vk_poster.py           ← runs Thursday
        ↓
scheduler.py           ← master controller, runs 24/7 on VPS
```

---

## Setup

### 1. Install dependencies

```bash
cd /opt/resumeaibot
pip3 install -r content_marketing/requirements_content.txt --break-system-packages
```

### 2. Add credentials to .env

Add these to `/opt/resumeaibot/.env`:

```bash
# Reddit (see below for how to get)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# VK (see below for how to get)
VK_ACCESS_TOKEN=your_vk_token
VK_OWNER_ID=-123456789    # your group ID (negative for groups)
```

---

## How to get Reddit API keys

**Step 1:** Create a Reddit account (or use existing).
Karma requirement: you need ~50+ karma to post in most subreddits.
Create the account, comment on a few posts to build karma first.

**Step 2:** Go to https://www.reddit.com/prefs/apps

**Step 3:** Click "create another app" (bottom of page)

**Step 4:** Fill in:
- Name: `ResumeAI Bot` (anything)
- Type: **script** ← important, not "web app"
- Description: leave blank
- Redirect URI: `http://localhost:8080` (required but not used)

**Step 5:** Click "create app"

**Step 6:** Copy values:
- `REDDIT_CLIENT_ID` = the 14-character string under your app name
- `REDDIT_CLIENT_SECRET` = the "secret" field
- `REDDIT_USERNAME` = your Reddit username
- `REDDIT_PASSWORD` = your Reddit password

**Important Reddit rules:**
- Wait 2+ weeks before posting to avoid spam filters
- First post 5–10 regular comments in target subreddits
- Never mention the bot in 100% of your posts (mix in genuine answers)
- r/resumes allows sharing tools; r/cscareerquestions is stricter

---

## How to get VK API token

**Step 1:** Go to https://vk.com/apps?act=manage

**Step 2:** Click "Create Application"

**Step 3:** Fill in:
- Title: `ResumeAI Content`
- Platform: **Standalone application**

**Step 4:** Click "Connect application", confirm

**Step 5:** Go to Settings → paste this URL in your browser, replacing APP_ID:
```
https://oauth.vk.com/authorize?client_id=APP_ID&display=page&redirect_uri=https://oauth.vk.com/blank.html&scope=wall,photos,groups,offline&response_type=token&v=5.131
```

**Step 6:** Allow access. You'll be redirected to a URL with `access_token=...` — copy that.

**Step 7:** Get your group ID:
- Go to your VK group
- Click "Manage"
- The group ID is in the URL: `https://vk.com/club123456789`
- Use `-123456789` (with minus) as `VK_OWNER_ID`

---

## Telegra.ph (Automatic)

No setup needed. On first run, `telegraph_publisher.py` automatically:
1. Creates a free Telegraph account
2. Saves the token to `content_marketing/logs/telegraph_token.txt`

---

## Starting the scheduler

### On VPS (systemd service)

```bash
# Create systemd service
cat > /etc/systemd/system/content-marketing.service << 'EOF'
[Unit]
Description=ResumeAI Content Marketing Scheduler
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/resumeaibot
EnvironmentFile=/opt/resumeaibot/.env
ExecStart=/usr/bin/python3 /opt/resumeaibot/content_marketing/scheduler.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable content-marketing.service
systemctl start content-marketing.service
systemctl status content-marketing.service
```

### Test everything first

```bash
cd /opt/resumeaibot

# Generate content for one topic (test)
python3 content_marketing/content_generator.py

# Preview Reddit post (no actual posting)
python3 content_marketing/reddit_poster.py --dry-run

# Preview Telegra.ph (no actual publishing)
python3 content_marketing/telegraph_publisher.py --dry-run

# Preview VK post (no actual posting)
python3 content_marketing/vk_poster.py --dry-run
```

---

## Deploy on Railway.app (free tier)

Railway gives you $5/month free credit — enough to run this scheduler 24/7.

**Step 1:** Push your repo to GitHub

**Step 2:** Go to https://railway.app → New Project → Deploy from GitHub repo

**Step 3:** Select your repo → Railway auto-detects Python

**Step 4:** Set environment variables in Railway dashboard (same as .env)

**Step 5:** Set the start command:
```
python3 content_marketing/scheduler.py
```

**Step 6:** Deploy. Railway keeps it running automatically.

---

## Expected Results Timeline

### Week 1
- Content generated for 1–2 topics
- First Reddit post live
- First Telegra.ph article published
- 0–5 organic views

### Month 1
- 4 Reddit posts live
- 8 Telegra.ph articles
- 4 VK posts
- Expected: 50–200 total organic impressions
- Bot clicks from content: 5–20

### Month 3
- 12+ Reddit posts, some gaining traction
- 24+ Telegra.ph articles (Google may start indexing them)
- 12+ VK posts
- Reddit karma building (allows posting in more subreddits)
- Expected: 500–2000 monthly organic impressions
- Bot clicks from content: 50–200/month

### Month 6
- Established presence in career subreddits
- Some Telegra.ph articles ranking in Google
- Expected: 2000–10000 monthly organic views
- Bot signups from content: 100–500/month

**Key success factors:**
1. Consistency (never skip weeks)
2. Quality > quantity (Claude generates good content)
3. Genuine engagement (reply to comments on Reddit posts)
4. Diversify beyond these platforms once traffic comes

---

## Logs

All logs are in `content_marketing/logs/`:
- `content_generation_log.txt` — content generation history
- `reddit_log.txt` — Reddit posting history
- `reddit_posted_log.json` — which posts have been published (prevents reposts)
- `telegraph_log.txt` — Telegra.ph publishing history
- `telegraph_published.json` — published article URLs
- `vk_log.txt` — VK posting history
- `master_scheduler_log.txt` — scheduler events and errors
