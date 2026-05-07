#!/usr/bin/env python3
"""
archive_legacy_ru_applications.py — one-shot migration script for the 2026-05 international pivot.

Actions:
  1. Sets status='archived_legacy_ru' for all applications where source IN ('hh','superjob','zarplata').
  2. Sets is_active=0 and pause_reason='legacy_ru_disabled' for campaigns that used those sources.

Run once after deploying the international-pivot worker.  Safe to re-run (idempotent).
"""
import argparse
import logging
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

_LEGACY_SOURCES = ("hh", "superjob", "zarplata")
_ARCHIVE_STATUS = "archived_legacy_ru"
_PAUSE_REASON   = "legacy_ru_disabled"


def archive(db_path: str, dry_run: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # -- 1. Applications ------------------------------------------------
        cur.execute(
            "SELECT COUNT(*) FROM applications WHERE source IN ({}) AND status != ?".format(
                ",".join("?" * len(_LEGACY_SOURCES))
            ),
            (*_LEGACY_SOURCES, _ARCHIVE_STATUS),
        )
        app_count = cur.fetchone()[0]
        log.info("Applications to archive: %d", app_count)

        if not dry_run and app_count:
            cur.execute(
                "UPDATE applications SET status=? WHERE source IN ({}) AND status != ?".format(
                    ",".join("?" * len(_LEGACY_SOURCES))
                ),
                (_ARCHIVE_STATUS, *_LEGACY_SOURCES, _ARCHIVE_STATUS),
            )
            log.info("Archived %d application rows", cur.rowcount)

        # -- 2. Campaigns ---------------------------------------------------
        # campaigns table may not have source column — check schema first
        cur.execute("PRAGMA table_info(campaigns)")
        campaign_cols = {row["name"] for row in cur.fetchall()}

        if "source" in campaign_cols and "is_active" in campaign_cols:
            cur.execute(
                "SELECT COUNT(*) FROM campaigns WHERE source IN ({}) AND is_active=1".format(
                    ",".join("?" * len(_LEGACY_SOURCES))
                ),
                _LEGACY_SOURCES,
            )
            camp_count = cur.fetchone()[0]
            log.info("Active campaigns to pause: %d", camp_count)

            if not dry_run and camp_count:
                pause_cols = campaign_cols & {"pause_reason"}
                if pause_cols:
                    cur.execute(
                        "UPDATE campaigns SET is_active=0, pause_reason=? "
                        "WHERE source IN ({}) AND is_active=1".format(
                            ",".join("?" * len(_LEGACY_SOURCES))
                        ),
                        (_PAUSE_REASON, *_LEGACY_SOURCES),
                    )
                else:
                    cur.execute(
                        "UPDATE campaigns SET is_active=0 "
                        "WHERE source IN ({}) AND is_active=1".format(
                            ",".join("?" * len(_LEGACY_SOURCES))
                        ),
                        _LEGACY_SOURCES,
                    )
                log.info("Paused %d campaign rows", cur.rowcount)
        else:
            log.info("campaigns table has no 'source' column — skipping campaign step")

        if dry_run:
            log.info("[DRY RUN] No changes written")
            conn.rollback()
        else:
            conn.commit()
            log.info("Done — committed all changes to %s", db_path)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db", nargs="?", default="/opt/resumeaibot/autoapply.db",
                        help="Path to autoapply SQLite database")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would change without writing anything")
    args = parser.parse_args()

    db_path = args.db
    if not Path(db_path).exists():
        log.error("Database not found: %s", db_path)
        sys.exit(1)

    archive(db_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
