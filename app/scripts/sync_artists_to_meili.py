"""
sync_artists_to_meili.py
────────────────────────
One-time (and safe-to-rerun) script that:
  1. Configures the Meilisearch 'artists' index settings.
  2. Reads all distinct (artist_name, song_count) pairs from PostgreSQL.
  3. Bulk-upserts them into the Meilisearch 'artists' index.

Run from the lyrics-api/ directory:
    python -m app.scripts.sync_artists_to_meili
"""

import sys
import os

# Ensure the project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import func
from app.core.database import SessionLocal
from app.models.song import Song
from app.services.search import (
    get_artists_index,
    ensure_artists_index_settings,
    _artist_id,
)


BATCH_SIZE = 500   # Meilisearch handles large batches fine; keep under 10 MB payload


def sync_all_artists():
    db = SessionLocal()
    try:
        # Step 1 — configure index settings (searchable attrs, ranking rules, etc.)
        print("Configuring 'artists' Meilisearch index settings ...")
        ensure_artists_index_settings()

        # Step 2 — fetch all artists + song counts from DB
        print("Querying PostgreSQL for all artists ...")
        rows = (
            db.query(Song.artist_name, func.count(Song.id).label("song_count"))
            .group_by(Song.artist_name)
            .order_by(func.count(Song.id).desc())
            .all()
        )
        total = len(rows)
        print(f"Found {total} unique artists in the database.")

        if total == 0:
            print("Nothing to sync. Exiting.")
            return

        # Step 3 — batch upsert into Meilisearch
        index = get_artists_index()
        batched = 0

        for i in range(0, total, BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            documents = [
                {
                    "id": _artist_id(row[0]),
                    "artist_name": row[0],
                    "song_count": row[1],
                }
                for row in batch
                if row[0]  # skip null artist names
            ]
            task = index.add_documents(documents)
            batched += len(documents)
            print(f"  Queued batch {i // BATCH_SIZE + 1}: {len(documents)} artists "
                  f"(task uid={task.task_uid}, total so far: {batched})")

        print(f"\nDone! {batched} artist documents queued to Meilisearch.")
        print("   Indexing is asynchronous; documents will be searchable in a few seconds.")

    finally:
        db.close()


if __name__ == "__main__":
    sync_all_artists()
