"""
Migration Script: sarigama_uploads_2.db -> PostgreSQL (songs_db)
================================================================
- Reads 718 songs from the new SQLite database
- Auto-generates r2_lrc_link from the song folder in r2_original_url
  Pattern: https://music.ifreaky.us/<Song-Folder>/lyrics.lrc
- Skips duplicates (matched by song_name + artist_name)
- After migration, syncs all new songs to Meilisearch

Usage (run from lyrics-api/ directory):
    python -m app.scripts.migrate_sqlite2_to_postgres

Or directly:
    python app/scripts/migrate_sqlite2_to_postgres.py
"""

import sys
import os
import sqlite3
import uuid
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path so we can import app modules
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal, Base, engine
from app.models.song import Song

# ─── Config ────────────────────────────────────────────────────────────────────
SQLITE_DB_FILENAME = "sarigama_uploads (6).db"
# ───────────────────────────────────────────────────────────────────────────────


def get_sqlite_db_path():
    """Resolve sarigama_uploads_2.db path relative to lyrics-api/ root."""
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", SQLITE_DB_FILENAME)
    )


def build_lrc_link(r2_original_url):
    """
    Auto-generate r2_lrc_link from the original music URL.

    Example:
        Input:  https://music.ifreaky.us/Dutuda-Indala-Luhu-Banda/original.mp3
        Output: https://music.ifreaky.us/Dutuda-Indala-Luhu-Banda/lyrics.lrc
    """
    if not r2_original_url:
        return None
    try:
        parsed = urlparse(r2_original_url)
        # Path looks like: /Dutuda-Indala-Luhu-Banda/original.mp3
        # We want:         /Dutuda-Indala-Luhu-Banda/lyrics.lrc
        parts = parsed.path.rsplit("/", 1)   # ['/<song-folder>', 'original.mp3']
        folder = parts[0]                    # /<song-folder>
        lrc_path = f"{folder}/lyrics.lrc"
        return f"{parsed.scheme}://{parsed.netloc}{lrc_path}"
    except Exception:
        return None


def migrate():
    db_path = get_sqlite_db_path()
    if not os.path.exists(db_path):
        print(f"[ERROR] SQLite file not found: {db_path}")
        print("        Make sure sarigama_uploads_2.db is in the lyrics-api/ directory.")
        return

    # Ensure PostgreSQL tables exist
    print("[1/4] Ensuring PostgreSQL tables exist...")
    Base.metadata.create_all(bind=engine)

    # Connect to SQLite
    print(f"[2/4] Reading from SQLite: {db_path}")
    sqlite_conn = sqlite3.connect(db_path)
    cursor = sqlite_conn.cursor()

    rows = cursor.execute(
        "SELECT song_name, artist_name, r2_original_url, r2_instrumental_url, r2_cover_url "
        "FROM uploads"
    ).fetchall()
    sqlite_conn.close()

    print(f"      Found {len(rows)} songs in SQLite.")

    # Migrate to PostgreSQL
    print("[3/4] Migrating to PostgreSQL...")
    db = SessionLocal()
    added = 0
    skipped = 0
    lrc_generated = 0

    for row in rows:
        song_name, artist_name, original_url, instrumental_url, cover_url = row

        # Skip duplicates
        existing = db.query(Song).filter(
            Song.song_name == song_name,
            Song.artist_name == artist_name
        ).first()

        if existing:
            skipped += 1
            continue

        # Auto-generate r2_lrc_link
        lrc_link = build_lrc_link(original_url)
        if lrc_link:
            lrc_generated += 1

        new_song = Song(
            id=uuid.uuid4(),
            song_name=song_name,
            artist_name=artist_name,
            original_music_link=original_url,
            instrumental_music_link=instrumental_url,
            cover_url=cover_url,
            r2_lrc_link=lrc_link,
            play_count=0,
        )
        db.add(new_song)
        added += 1

    db.commit()
    db.close()

    print(f"\nMigration complete!")
    print(f"  Added   : {added} songs")
    print(f"  Skipped : {skipped} songs (already in PostgreSQL)")
    print(f"  LRC links auto-generated: {lrc_generated}")


def sync_to_meilisearch():
    """Sync all PostgreSQL songs to Meilisearch after migration."""
    print("\n[4/4] Syncing to Meilisearch...")
    try:
        from app.services.search import get_songs_index
        db = SessionLocal()
        songs = db.query(Song).all()

        documents = []
        for s in songs:
            documents.append({
                "id": str(s.id),
                "song_name": s.song_name,
                "artist_name": s.artist_name,
                "original_music_link": s.original_music_link,
                "instrumental_music_link": s.instrumental_music_link,
                "cover_url": s.cover_url,
                "r2_lrc_link": s.r2_lrc_link,
            })

        db.close()

        if documents:
            index = get_songs_index()
            task = index.add_documents(documents)
            print(f"Meilisearch sync triggered! Task ID: {task.task_uid}")
            print(f"  Total documents in index: {len(documents)}")
        else:
            print("  No documents to sync.")
    except Exception as e:
        print(f"WARNING: Meilisearch sync failed (non-critical): {e}")
        print("  You can run sync_db_to_meili.py separately later.")


if __name__ == "__main__":
    migrate()
    sync_to_meilisearch()
