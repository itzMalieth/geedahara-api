#!/usr/bin/env python3
"""
Seed Lyrics Metadata from SQLite Scanned Records into PostgreSQL
================================================================
Reads `lrc-generator/r2_music_records.db` and populates:
  - has_lrc
  - has_full_lyrics
  - full_lyrics_format
  - r2_folder
  - lyrics_updated_at
into the PostgreSQL `songs` table.
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import execute_batch

def main():
    # Resolve paths
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    sqlite_db_path = project_root / "lrc-generator" / "r2_music_records.db"

    if not sqlite_db_path.exists():
        print(f"Error: SQLite database not found at {sqlite_db_path}")
        print("Please run `python lrc-generator/scan_r2_records.py` first.")
        sys.exit(1)

    print(f"[*] Reading SQLite records from: {sqlite_db_path}")
    sqlite_conn = sqlite3.connect(str(sqlite_db_path))
    sqlite_cur = sqlite_conn.cursor()

    sqlite_cur.execute("""
        SELECT folder_name, has_lrc, lrc_key, has_full_lyrics_txt, full_lyrics_txt_key,
               has_full_lyrics_json, full_lyrics_json_key, has_any_lyrics
        FROM songs
    """)
    sqlite_rows = sqlite_cur.fetchall()
    sqlite_conn.close()

    print(f"[+] Loaded {len(sqlite_rows)} song records from SQLite.")

    # Connect to PostgreSQL
    pg_dsn = "postgresql://postgres:admin@localhost:5432/songs_db"
    try:
        pg_conn = psycopg2.connect(pg_dsn)
        pg_conn.autocommit = False
        pg_cur = pg_conn.cursor()
    except Exception as e:
        print(f"Error connecting to PostgreSQL ({pg_dsn}): {e}")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    updated_count = 0
    lyrics_count = 0
    matched_count = 0

    print("[*] Updating PostgreSQL songs table...")

    for row in sqlite_rows:
        folder_name = row[0]
        has_lrc = bool(row[1])
        lrc_key = row[2]
        has_full_txt = bool(row[3])
        full_txt_key = row[4]
        has_full_json = bool(row[5])
        full_json_key = row[6]
        has_any = bool(row[7])

        has_full = has_full_txt or has_full_json
        fmt = 'json' if has_full_json else ('txt' if has_full_txt else None)

        lrc_link = f"https://music.ifreaky.us/{lrc_key}" if lrc_key else None
        full_link = f"https://music.ifreaky.us/{full_json_key if has_full_json else full_txt_key}" if (has_full_json or has_full_txt) else None
        updated_at = now if has_any else None

        # Try matching by original_music_link containing the folder or exact slug
        pg_cur.execute("""
            UPDATE songs
            SET r2_folder = %s,
                has_lrc = %s,
                has_full_lyrics = %s,
                full_lyrics_format = %s,
                r2_lrc_link = COALESCE(%s, r2_lrc_link),
                r2_full_lyrics_link = COALESCE(%s, r2_full_lyrics_link),
                lyrics_updated_at = CASE WHEN %s IS TRUE THEN %s ELSE lyrics_updated_at END
            WHERE original_music_link ILIKE %s OR r2_folder = %s
            RETURNING id;
        """, (
            folder_name,
            has_lrc,
            has_full,
            fmt,
            lrc_link,
            full_link,
            has_any,
            updated_at,
            f"%/{folder_name}/%",
            folder_name
        ))

        matched = pg_cur.fetchall()
        if matched:
            matched_count += len(matched)
            if has_any:
                lyrics_count += len(matched)

    pg_conn.commit()
    pg_conn.close()

    print("\n" + "=" * 60)
    print("        POSTGRESQL LYRICS SEED COMPLETE")
    print("=" * 60)
    print(f" Total SQLite Records Scanned : {len(sqlite_rows):,}")
    print(f" PostgreSQL Songs Matched    : {matched_count:,}")
    print(f" Songs Populated with Lyrics : {lyrics_count:,}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
