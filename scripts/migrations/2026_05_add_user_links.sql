-- 2026-05 P04: Unified Telegram↔AutoApply identity
-- Run once against autoapply.db. Safe to re-run (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS user_links (
    telegram_id       INTEGER PRIMARY KEY,
    autoapply_user_id INTEGER NOT NULL REFERENCES autoapply_users(id),
    linked_at         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS used_link_jti (
    jti     TEXT PRIMARY KEY,
    used_at REAL NOT NULL
);
