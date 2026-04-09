#!/usr/bin/env python3
"""
vk_poster.py — Posts content to a VK group/page.

Uses vk_api library. Reads VK_ACCESS_TOKEN and VK_OWNER_ID from .env.
Posts max 1 time per day. Logs to vk_log.txt.

Usage:
    python3 vk_poster.py           # post next unposted VK content
    python3 vk_poster.py --dry-run # preview without posting
"""

import json
import logging
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from content_marketing.config import (
    VK_ACCESS_TOKEN,
    VK_OWNER_ID,
    CONTENT_DIR,
    LOGS_DIR,
    BOT_LINK,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "vk_log.txt", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

POSTED_LOG = LOGS_DIR / "vk_posted_log.json"


def load_posted_log() -> dict:
    if POSTED_LOG.exists():
        return json.loads(POSTED_LOG.read_text(encoding="utf-8"))
    return {}


def save_posted_log(data: dict) -> None:
    POSTED_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def posted_today(posted: dict) -> bool:
    """Check if we already posted to VK today."""
    today = date.today().isoformat()
    return any(
        entry.get("posted_at", "")[:10] == today
        for entry in posted.values()
    )


def get_next_post() -> tuple[str, str] | None:
    """
    Find the oldest unposted vk_post.txt.
    Returns (folder_name, post_text) or None.
    """
    posted = load_posted_log()
    already_done = set(posted.keys())

    folders = sorted(
        [d for d in CONTENT_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name
    )

    for folder in folders:
        vk_file = folder / "vk_post.txt"
        if not vk_file.exists():
            continue
        if folder.name in already_done:
            continue

        text = vk_file.read_text(encoding="utf-8").strip()
        if text:
            return folder.name, text

    return None


def post_to_vk(text: str, image_path: Path | None = None, dry_run: bool = False) -> int | None:
    """
    Post to VK wall. Returns post_id on success, None on failure.
    Optionally attaches an image if image_path exists.
    """
    if dry_run:
        log.info("[DRY RUN] Would post to VK (owner_id=%s):\n%s", VK_OWNER_ID, text[:300])
        return 999999

    try:
        import vk_api
    except ImportError:
        log.error("vk_api not installed — run: pip install vk_api")
        return None

    vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
    vk = vk_session.get_api()

    attachments = []

    # Upload image if provided and exists
    if image_path and image_path.exists():
        try:
            from vk_api.upload import VkUpload
            upload = VkUpload(vk_session)
            photo = upload.photo_wall(str(image_path), group_id=abs(int(VK_OWNER_ID)))
            photo_id = photo[0]
            attachments.append(f"photo{photo_id['owner_id']}_{photo_id['id']}")
            log.info("Image uploaded: %s", attachments[-1])
        except Exception as e:
            log.warning("Image upload failed (posting without image): %s", e)

    kwargs = {
        "owner_id": VK_OWNER_ID,
        "message":  text,
        "from_group": 1,
    }
    if attachments:
        kwargs["attachments"] = ",".join(attachments)

    response = vk.wall.post(**kwargs)
    post_id = response.get("post_id")
    log.info("✅ Posted to VK: post_id=%s", post_id)
    return post_id


def main(dry_run: bool = False):
    if not VK_ACCESS_TOKEN or not VK_OWNER_ID:
        log.error("VK credentials not configured. Set VK_ACCESS_TOKEN and VK_OWNER_ID in .env")
        sys.exit(1)

    posted = load_posted_log()

    # Max 1 post per day
    if posted_today(posted) and not dry_run:
        log.info("Already posted to VK today — skipping.")
        return

    result = get_next_post()
    if not result:
        log.info("No unposted VK content found. Run content_generator.py first.")
        return

    folder_name, text = result
    log.info("Posting to VK: %s chars", len(text))

    # Check for optional image
    image_path = CONTENT_DIR / folder_name / "image.png"

    post_id = post_to_vk(text, image_path if image_path.exists() else None, dry_run=dry_run)

    if post_id:
        posted[folder_name] = {
            "post_id": post_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        save_posted_log(posted)
        log.info("Saved to VK posted log.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
