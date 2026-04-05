#!/usr/bin/env python3
"""
Reads current cloudflared tunnel URL from logs,
updates .env, and sets the Telegram Menu Button automatically.
Runs once at startup via systemd (after cloudflared-tunnel.service).
"""
import re, os, time, subprocess, urllib.request, json, sys

BOT_TOKEN = "8442677408:AAFGf_Y14ZZntTVipyA5VQgeGNFenpJ_iQk"
ENV_FILE  = "/opt/resumeaibot/.env"
LOG_FILE  = "/var/log/cloudflared.log"


def get_tunnel_url(retries=20):
    for i in range(retries):
        try:
            with open(LOG_FILE) as f:
                content = f.read()
            m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', content)
            if m:
                return m.group(0)
        except FileNotFoundError:
            pass
        print(f"Waiting for tunnel URL... ({i+1}/{retries})")
        time.sleep(3)
    return None


def update_env(url):
    with open(ENV_FILE) as f:
        lines = f.readlines()
    new_lines = []
    found = False
    for line in lines:
        if line.startswith("WEBAPP_URL="):
            new_lines.append(f"WEBAPP_URL={url}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"WEBAPP_URL={url}\n")
    with open(ENV_FILE, "w") as f:
        f.writelines(new_lines)
    print(f"Updated .env: WEBAPP_URL={url}")


def set_telegram_menu_button(url):
    payload = json.dumps({
        "menu_button": {
            "type": "web_app",
            "text": "\U0001f310 \u041e\u0442\u043a\u0440\u044b\u0442\u044c Mini App",
            "web_app": {"url": url}
        }
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setChatMenuButton",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                print(f"Telegram menu button set to: {url}")
            else:
                print(f"Telegram API response: {result}")
    except Exception as e:
        print(f"Could not set menu button: {e}")


if __name__ == "__main__":
    print("Waiting for cloudflared tunnel URL...")
    url = get_tunnel_url()
    if not url:
        print("ERROR: Could not find tunnel URL in logs")
        sys.exit(1)
    print(f"Got URL: {url}")
    update_env(url)
    set_telegram_menu_button(url)
    subprocess.run(["systemctl", "restart", "resumeaibot"], check=True)
    print("Bot restarted with new URL.")
