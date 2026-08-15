import sys
import os
import sqlite3
import uuid
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal, Base, engine
from app.models.song import Song
from app.services.search import get_songs_index

def migrate_sqlite_to_postgres():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sarigama_uploads.db"))
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found!")
        return

    print("Connecting to PostgreSQL & creating tables if needed...")
    Base.metadata.create_all(bind=engine)

    print(f"Connecting to SQLite database at: {db_path}")
    sqlite_conn = sqlite3.connect(db_path)
    cursor = sqlite_conn.cursor()

    rows = cursor.execute("SELECT song_name, artist_name, r2_original_url, r2_instrumental_url FROM uploads").fetchall()
    print(f"Found {len(rows)} songs in SQLite database.")

    db = SessionLocal()
    added_count = 0
    skipped_count = 0

    for row in rows:
        song_name, artist_name, original_url, instrumental_url = row
        
        # Check if song already exists in PostgreSQL to avoid duplicates
        existing = db.query(Song).filter(
            Song.song_name == song_name,
            Song.artist_name == artist_name
        ).first()

        if existing:
            skipped_count += 1
            continue

        new_song = Song(
            id=uuid.uuid4(),
            song_name=song_name,
            artist_name=artist_name,
            original_music_link=original_url,
            instrumental_music_link=instrumental_url,
            play_count=0
        )
        db.add(new_song)
        added_count += 1

    db.commit()
    db.close()
    sqlite_conn.close()

    print(f"Migration completed successfully!")
    print(f"Added to PostgreSQL: {added_count} songs")
    print(f"Skipped (already exists): {skipped_count} songs")

def sync_all_to_meili():
    print("Syncing all PostgreSQL songs to Meilisearch...")
    db = SessionLocal()
    songs = db.query(Song).all()
    index = get_songs_index()
    
    meili_docs = []
    for s in songs:
        meili_docs.append({
            "id": str(s.id),
            "song_name": s.song_name,
            "artist_name": s.artist_name,
            "original_music_link": s.original_music_link,
            "instrumental_music_link": s.instrumental_music_link
        })
    
    if meili_docs:
        index.add_documents(meili_docs)
        print(f"Successfully synced {len(meili_docs)} songs to Meilisearch!")

if __name__ == "__main__":
    migrate_sqlite_to_postgres()
    sync_all_to_meili()
