-- 2026-05 P05: Single Portfolio System
-- Run once against autoapply.db. Safe to re-run (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS portfolios (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    autoapply_user_id   INTEGER UNIQUE NOT NULL REFERENCES autoapply_users(id),
    handle              TEXT    UNIQUE,
    headline            TEXT,
    bio                 TEXT,
    country             TEXT,
    timezone            TEXT,
    hire_status         TEXT    DEFAULT 'open',
    resume_blob_json    TEXT,
    updated_at          TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS portfolio_assets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    kind         TEXT    NOT NULL CHECK(kind IN ('photo','file')),
    url          TEXT    NOT NULL,
    sort_order   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS portfolio_links (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    label        TEXT    NOT NULL,
    url          TEXT    NOT NULL,
    kind         TEXT    NOT NULL CHECK(kind IN ('social','messenger','website')),
    sort_order   INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_portfolios_handle ON portfolios(handle);
CREATE INDEX IF NOT EXISTS idx_portfolio_assets_portfolio ON portfolio_assets(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_links_portfolio ON portfolio_links(portfolio_id);
