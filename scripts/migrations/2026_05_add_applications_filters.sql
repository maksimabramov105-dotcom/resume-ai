-- Migration: 2026_05_add_applications_filters
-- Adds user-facing status tracking and view preferences for the applications hub (P07).
--
-- run once — safe to re-run if already applied
-- SQLite will raise "duplicate column name" if a column already exists — that is OK to ignore.

ALTER TABLE applications ADD COLUMN user_status TEXT DEFAULT 'active';

ALTER TABLE applications ADD COLUMN withdrawn_at TEXT;

ALTER TABLE applications ADD COLUMN last_user_action_at TEXT;

ALTER TABLE autoapply_users ADD COLUMN view_prefs TEXT;

-- Index for tab-count queries and user_status filtering
CREATE INDEX IF NOT EXISTS idx_applications_user_status ON applications(user_id, user_status, sent_at);
