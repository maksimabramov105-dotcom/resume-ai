-- Migration: 2026_05_add_company_country
-- Adds company_country column to applications table.
-- Idempotent: SQLite ignores the ALTER if the column already exists
-- (handled by the "duplicate column name" error being caught in init_db).
--
-- To run manually on VPS:
--   sqlite3 /opt/resumeaibot/autoapply.db < scripts/migrations/2026_05_add_company_country.sql

ALTER TABLE applications ADD COLUMN company_country TEXT;
