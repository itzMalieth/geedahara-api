-- Phase 3 Migration: Add deleted_at column to users table for soft account deletion
BEGIN;

ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- Add an index on deleted_at since we will filter out deleted users frequently
CREATE INDEX IF NOT EXISTS ix_users_deleted_at ON users(deleted_at);

COMMIT;
