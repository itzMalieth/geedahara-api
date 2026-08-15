import sys
import os
import sqlite3
import uuid
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.database import SessionLocal, Base, engine
from app.models.song import Song
from app.models.user import User
from app.models.playlist import Playlist
from app.models.history import ListeningHistory
from app.services.search import get_songs_index

def reset_and_migrate():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sarigama_uploads.db"))
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found!")
        return

    print("Step 1: Dropping old PostgreSQL tables & recreating schema...")
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception as e:
        print(f"Notice during drop_all: {e}")
    
    Base.metadata.create_all(bind=engine)
    print("Schema recreated successfully.")

    print("\nStep 2: Clearing Meilisearch index...")
    try:
        index = get_songs_index()
        index.delete_all_documents()
        print("Meilisearch index cleared.")
    except Exception as e:
        print(f"Meilisearch notice: {e}")

    print(f"\nStep 3: Reading SQLite database at {db_path}...")
    sqlite_conn = sqlite3.connect(db_path)
    cursor = sqlite_conn.cursor()

    rows = cursor.execute(
        "SELECT song_name, artist_name, r2_original_url, r2_instrumental_url, r2_cover_url FROM uploads"
    ).fetchall()
    print(f"Found {len(rows)} songs in SQLite database.")

    print("\nStep 4: Migrating records to PostgreSQL & Meilisearch...")
    db = SessionLocal()
    meili_docs = []

    for row in rows:
        song_name, artist_name, original_url, instrumental_url, cover_url = row

        song_id = uuid.uuid4()
        new_song = Song(
            id=song_id,
            song_name=song_name,
            artist_name=artist_name,
            original_music_link=original_url,
            instrumental_music_link=instrumental_url,
            cover_url=cover_url,
            play_count=0
        )
        db.add(new_song)

        meili_docs.append({
            "id": str(song_id),
            "song_name": song_name,
            "artist_name": artist_name,
            "original_music_link": original_url,
            "instrumental_music_link": instrumental_url,
            "cover_url": cover_url,
        })

    db.commit()
    db.close()
    sqlite_conn.close()

    print(f"Saved {len(rows)} songs to PostgreSQL.")

    print("\nStep 5: Batch indexing to Meilisearch...")
    try:
        index = get_songs_index()
        index.add_documents(meili_docs)
        print(f"Successfully indexed {len(meili_docs)} songs in Meilisearch!")
    except Exception as e:
        print(f"Meilisearch batch error: {e}")

    print("\nReset and Migration Complete Successfully!")

if __name__ == "__main__":
    reset_and_migrate()
