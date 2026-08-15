-- ============================================================
-- HelaGee Auth Phase 1 Migration
-- Run against your PostgreSQL database (songs_db)
-- ============================================================
-- This migration:
--   1. Renames google_id → google_sub (matches OIDC spec)
--   2. Adds role column (default 'user')
--   3. Adds updated_at TIMESTAMPTZ column
--   4. Changes created_at to TIMESTAMPTZ (timezone-aware UTC)
-- ============================================================

BEGIN;

-- 1. Rename google_id to google_sub
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='users' AND column_name='google_id'
    ) THEN
        ALTER TABLE users RENAME COLUMN google_id TO google_sub;
        RAISE NOTICE 'Renamed google_id -> google_sub';
    ELSE
        RAISE NOTICE 'Column google_sub already exists or google_id not found, skipping rename';
    END IF;
END $$;

-- 2. Add role column if missing
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) NOT NULL DEFAULT 'user';

-- 3. Add updated_at column if missing
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- 4. Upgrade created_at to TIMESTAMPTZ if it's plain TIMESTAMP
-- (Postgres will keep the data, just attaches UTC timezone)
DO $$
DECLARE
    col_type TEXT;
BEGIN
    SELECT data_type INTO col_type
    FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'created_at';

    IF col_type = 'timestamp without time zone' THEN
        ALTER TABLE users
            ALTER COLUMN created_at TYPE TIMESTAMPTZ
            USING created_at AT TIME ZONE 'UTC';
        RAISE NOTICE 'Upgraded created_at to TIMESTAMPTZ';
    ELSE
        RAISE NOTICE 'created_at already TIMESTAMPTZ or not found, skipping';
    END IF;
END $$;

COMMIT;

-- Verify
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position;
