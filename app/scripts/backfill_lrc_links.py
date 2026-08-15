"""
Backfill r2_lrc_link for songs that already exist in PostgreSQL
but are missing the r2_lrc_link value.

Matches by song_name + artist_name from sarigama_uploads_2.db,
derives the lrc link from r2_original_url.

Usage:
    .\\venv\\Scripts\\python.exe app/scripts/backfill_lrc_links.py
"""

import sys
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal
from app.models.song import Song

SQLITE_DB_FILENAME = "sarigama_uploads_2.db"


def build_lrc_link(r2_original_url):
    """
    Derive lrc URL from original mp3 URL.
    https://music.ifreaky.us/Song-Name/original.mp3
    -> https://music.ifreaky.us/Song-Name/lyrics.lrc
    """
    if not r2_original_url:
        return None
    try:
        parsed = urlparse(r2_original_url)
        folder = parsed.path.rsplit("/", 1)[0]
        return f"{parsed.scheme}://{parsed.netloc}{folder}/lyrics.lrc"
    except Exception:
        return None


def backfill():
    db_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", SQLITE_DB_FILENAME)
    )

    print(f"Reading from SQLite: {db_path}")
    sqlite_conn = sqlite3.connect(db_path)
    cursor = sqlite_conn.cursor()
    rows = cursor.execute(
        "SELECT song_name, artist_name, r2_original_url FROM uploads"
    ).fetchall()
    sqlite_conn.close()
    print(f"Loaded {len(rows)} rows from SQLite.")

    db = SessionLocal()
    updated = 0
    skipped_no_match = 0
    skipped_already_set = 0

    for song_name, artist_name, original_url in rows:
        song = db.query(Song).filter(
            Song.song_name == song_name,
            Song.artist_name == artist_name
        ).first()

        if not song:
            skipped_no_match += 1
            continue

        if song.r2_lrc_link:
            skipped_already_set += 1
            continue

        lrc = build_lrc_link(original_url)
        if lrc:
            song.r2_lrc_link = lrc
            updated += 1

    db.commit()
    db.close()

    print(f"\nBackfill complete!")
    print(f"  Updated          : {updated} songs")
    print(f"  Already had LRC  : {skipped_already_set} songs")
    print(f"  No DB match      : {skipped_no_match} songs")


if __name__ == "__main__":
    backfill()
