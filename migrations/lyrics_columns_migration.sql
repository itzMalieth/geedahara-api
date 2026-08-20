-- ============================================================
-- Lyrics Metadata Migration
-- Adds verified lyrics flags, format, and updated_at tracking
-- ============================================================

BEGIN;

-- 1. Add lyrics presence flags and format
ALTER TABLE songs ADD COLUMN IF NOT EXISTS has_lrc BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE songs ADD COLUMN IF NOT EXISTS has_full_lyrics BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE songs ADD COLUMN IF NOT EXISTS full_lyrics_format VARCHAR(10) NULL;
ALTER TABLE songs ADD COLUMN IF NOT EXISTS r2_folder VARCHAR(255) NULL;
ALTER TABLE songs ADD COLUMN IF NOT EXISTS lyrics_updated_at TIMESTAMPTZ NULL;

-- 2. Create indexes for fast filtering and sorting
CREATE INDEX IF NOT EXISTS idx_songs_has_lrc ON songs(has_lrc);
CREATE INDEX IF NOT EXISTS idx_songs_has_full_lyrics ON songs(has_full_lyrics);
CREATE INDEX IF NOT EXISTS idx_songs_r2_folder ON songs(r2_folder);
CREATE INDEX IF NOT EXISTS idx_songs_lyrics_updated_at ON songs(lyrics_updated_at DESC);

COMMIT;
