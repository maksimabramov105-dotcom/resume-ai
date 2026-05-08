-- P08: Reply Inbox — app_threads + app_messages
-- Run manually or via init_db() (CREATE TABLE IF NOT EXISTS is idempotent).

CREATE TABLE IF NOT EXISTS app_threads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id  INTEGER UNIQUE REFERENCES applications(id),
    user_id         INTEGER NOT NULL REFERENCES autoapply_users(id),
    company_email   TEXT,
    company_name    TEXT,
    reply_to_addr   TEXT,
    last_message_at TEXT DEFAULT (datetime('now')),
    status          TEXT DEFAULT 'open'
        CHECK(status IN ('open','closed','recruiter_replied','rejected'))
);

CREATE TABLE IF NOT EXISTS app_messages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id    INTEGER NOT NULL REFERENCES app_threads(id) ON DELETE CASCADE,
    direction    TEXT NOT NULL CHECK(direction IN ('out','in')),
    subject      TEXT,
    body_text    TEXT,
    body_html    TEXT,
    message_id   TEXT,
    in_reply_to  TEXT,
    received_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_app_threads_user ON app_threads(user_id, last_message_at);
CREATE INDEX IF NOT EXISTS idx_app_messages_thread ON app_messages(thread_id, received_at);
