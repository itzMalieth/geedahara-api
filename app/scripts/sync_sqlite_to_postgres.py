#!/usr/bin/env python3
"""
Sync missing songs from SQLite (sarigama_pipeline/music_app_sqlite.db) to PostgreSQL (songs_db)
=============================================================================================
- Reads all 9,974+ songs from SQLite
- Checks PostgreSQL for existing songs (by ID, original_music_link, or song_name+artist_name)
- Inserts any missing songs into PostgreSQL in efficient batches
- Reports initial count, newly added count, and final PostgreSQL count.

Usage (from lyrics-api directory):
    python app/scripts/sync_sqlite_to_postgres.py
"""

import sys
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal, engine, Base
from app.models.song import Song
from sqlalchemy.dialects.postgresql import insert as pg_insert


def get_sqlite_db_path():
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "sarigama_pipeline", "music_app_sqlite.db")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "music_app_sqlite.db")),
        "sarigama_pipeline/music_app_sqlite.db",
        "music_app_sqlite.db",
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("Could not find music_app_sqlite.db")


def sync_sqlite_to_postgres():
    sqlite_path = get_sqlite_db_path()
    print(f"\n{'='*75}")
    print("  SQLITE -> POSTGRESQL DATABASE SYNC")
    print(f"  Source SQLite DB : {sqlite_path}")
    print(f"{'='*75}\n")

    # 1. Connect SQLite
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    sqlite_rows = conn.execute("SELECT * FROM songs").fetchall()
    conn.close()

    print(f"[1/3] Found {len(sqlite_rows)} total songs in SQLite.")

    # 2. Connect PostgreSQL & Pre-fetch existing songs for fast lookup
    db = SessionLocal()

    print("[2/3] Fetching existing PostgreSQL records...")
    existing_pg_songs = db.query(Song).all()

    existing_ids = {str(s.id).lower() for s in existing_pg_songs if s.id}
    existing_links = {s.original_music_link.strip().lower() for s in existing_pg_songs if s.original_music_link}
    existing_names = {f"{s.song_name.strip().lower()}|||{s.artist_name.strip().lower()}" for s in existing_pg_songs if s.song_name and s.artist_name}

    initial_pg_count = len(existing_pg_songs)
    print(f"      PostgreSQL currently has {initial_pg_count} songs.")

    # 3. Filter missing songs and insert
    print("\n[3/3] Syncing missing songs to PostgreSQL...")

    added_count = 0
    batch = []
    BATCH_SIZE = 500

    for idx, row in enumerate(sqlite_rows, 1):
        r_dict = dict(row)

        s_id = str(r_dict.get("id") or uuid.uuid4()).lower()
        s_name = (r_dict.get("song_name") or "").strip()
        a_name = (r_dict.get("artist_name") or "").strip()
        orig_link = (r_dict.get("original_music_link") or "").strip()
        inst_link = (r_dict.get("instrumental_music_link") or "").strip()
        cover_url = (r_dict.get("cover_url") or "").strip()
        lrc_link = (r_dict.get("r2_lrc_link") or "").strip()
        play_cnt = int(r_dict.get("play_count") or 0)
        created_at_val = r_dict.get("created_at")

        if not s_name or not a_name:
            continue

        # Dedup checks
        name_key = f"{s_name.lower()}|||{a_name.lower()}"
        if s_id in existing_ids:
            continue
        if orig_link and orig_link.lower() in existing_links:
            continue
        if name_key in existing_names:
            continue

        # Parse created_at
        created_dt = datetime.now(timezone.utc)
        if created_at_val:
            try:
                created_dt = datetime.fromisoformat(created_at_val.replace("Z", "+00:00"))
            except Exception:
                pass

        # Try parsing ID as UUID, fallback to new UUID if invalid string
        try:
            song_uuid = uuid.UUID(s_id)
        except Exception:
            song_uuid = uuid.uuid4()

        new_song = Song(
            id=song_uuid,
            song_name=s_name,
            artist_name=a_name,
            original_music_link=orig_link if orig_link else None,
            instrumental_music_link=inst_link if inst_link else None,
            cover_url=cover_url if cover_url else None,
            play_count=play_cnt,
            created_at=created_dt.replace(tzinfo=None),  # Postgres TIMESTAMP WITHOUT TIME ZONE
            r2_lrc_link=lrc_link if lrc_link else None,
        )

        batch.append(new_song)
        existing_ids.add(str(song_uuid).lower())
        if orig_link:
            existing_links.add(orig_link.lower())
        existing_names.add(name_key)
        added_count += 1

        if len(batch) >= BATCH_SIZE:
            db.bulk_save_objects(batch)
            db.commit()
            print(f"      Batch committed: {added_count} new songs added so far...")
            batch = []

    if batch:
        db.bulk_save_objects(batch)
        db.commit()
        print(f"      Final batch committed: {added_count} total new songs added.")

    final_pg_count = db.query(Song).count()
    db.close()

    print(f"\n{'='*75}")
    print("  POSTGRESQL SYNC COMPLETE!")
    print(f"  Initial PostgreSQL Song Count : {initial_pg_count}")
    print(f"  Newly Inserted Songs          : {added_count}")
    print(f"  Final PostgreSQL Song Count   : {final_pg_count}")
    print(f"{'='*75}\n")

    return final_pg_count


if __name__ == "__main__":
    sync_sqlite_to_postgres()
