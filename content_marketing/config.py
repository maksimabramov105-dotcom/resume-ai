"""
content_marketing/config.py — All credentials for the content marketing system.

HOW TO FILL IN:
  1. Copy .env.content.example → .env  (or add these vars to your existing .env)
  2. Fill in your Reddit, VK credentials
  3. Anthropic + Telegram keys are already in your main .env

Never commit actual secrets to git.
"""
import os

# ── Existing project keys (already in .env) ─────────────────────────────────
# We reuse OpenRouter which supports Claude models via OpenAI-compatible API
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Claude model via OpenRouter (haiku is fast and cheap for content generation)
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "anthropic/claude-3-5-haiku")

BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
MY_CHAT_ID   = int(os.getenv("ADMIN_ID", "6246429438"))   # already set in .env

BOT_USERNAME = "topbestworkerbot"
BOT_LINK     = "https://t.me/topbestworkerbot"
BOT_NAME     = "РезюмеАИ"

# ── Reddit ───────────────────────────────────────────────────────────────────
# Get these at https://www.reddit.com/prefs/apps → "script" app type
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USERNAME      = os.getenv("REDDIT_USERNAME", "")
REDDIT_PASSWORD      = os.getenv("REDDIT_PASSWORD", "")
REDDIT_USER_AGENT    = os.getenv("REDDIT_USER_AGENT", "ResumeAI_ContentBot/1.0")

# ── VK ───────────────────────────────────────────────────────────────────────
# Get token at https://vk.com/editapp (create standalone app, use implicit flow)
VK_ACCESS_TOKEN = os.getenv("VK_ACCESS_TOKEN", "")
# Your VK group/page ID — negative number for groups (e.g. -123456789)
VK_OWNER_ID     = os.getenv("VK_OWNER_ID", "")

# ── Paths ────────────────────────────────────────────────────────────────────
import pathlib
BASE_DIR        = pathlib.Path(__file__).parent
CONTENT_DIR     = BASE_DIR / "content_output"
LOGS_DIR        = BASE_DIR / "logs"

CONTENT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── Validation helper ────────────────────────────────────────────────────────
def check_required(keys: list[str]) -> list[str]:
    """Returns list of missing env var names."""
    return [k for k in keys if not globals().get(k)]
