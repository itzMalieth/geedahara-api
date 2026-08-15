#!/usr/bin/env python3
"""
Sync all PostgreSQL Songs & Artists to Meilisearch
=================================================
- Auto-detects local/docker Meilisearch URL (7800 or 7700)
- Reads all 9,974+ songs from PostgreSQL (songs_db)
- Upserts all song documents into Meilisearch 'songs' index in batches
- Aggregates artist song counts and upserts all artist documents into Meilisearch 'artists' index
- Updates searchable and filterable attributes for instant search performance

Usage (from lyrics-api directory):
    python app/scripts/sync_db_to_meili.py
"""

import sys
import os
import re
import requests
import meilisearch
from pathlib import Path
from typing import List, Dict

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.song import Song


def get_active_meili_client():
    """Auto-detect active Meilisearch URL (e.g. 7800 on host dev, 7700 in docker)."""
    urls_to_try = [
        "http://127.0.0.1:7800",
        "http://localhost:7800",
        settings.MEILI_URL,
        "http://127.0.0.1:7700",
        "http://localhost:7700",
    ]

    key = settings.MEILI_MASTER_KEY or "aSampleMasterKey"

    for url in urls_to_try:
        try:
            r = requests.get(f"{url}/health", timeout=3)
            if r.status_code == 200:
                print(f"[Meilisearch] Connected to active instance at: {url}")
                return meilisearch.Client(url, key)
        except Exception:
            pass

    raise ConnectionError(f"Could not connect to Meilisearch at any of: {urls_to_try}")


def _artist_id(name: str) -> str:
    """Generate safe document ID for artist."""
    return re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')


def sync_all_to_meili():
    print(f"\n{'='*75}")
    print("  POSTGRESQL -> MEILISEARCH FULL DATABASE SYNC")
    print(f"{'='*75}\n")

    client = get_active_meili_client()
    db = SessionLocal()

    # 1. Read all songs from PostgreSQL
    print("[1/4] Fetching all songs from PostgreSQL...")
    songs = db.query(Song).all()
    total_songs = len(songs)

    if not songs:
        print("[!] No songs found in PostgreSQL. Database is empty.")
        db.close()
        return

    print(f"      Found {total_songs} songs in PostgreSQL database.")

    # 2. Prepare payload & artist aggregation
    print("[2/4] Preparing song payloads & building artist statistics...")

    song_documents = []
    artist_counts: Dict[str, int] = {}
    artist_covers: Dict[str, str] = {}

    for s in songs:
        s_id = str(s.id)
        s_name = s.song_name or ""
        a_name = s.artist_name or "Unknown Artist"

        song_documents.append({
            "id": s_id,
            "song_name": s_name,
            "artist_name": a_name,
            "original_music_link": s.original_music_link,
            "instrumental_music_link": s.instrumental_music_link,
            "cover_url": s.cover_url,
            "r2_lrc_link": s.r2_lrc_link,
            "play_count": s.play_count or 0,
        })

        if a_name:
            artist_counts[a_name] = artist_counts.get(a_name, 0) + 1
            if s.cover_url and a_name not in artist_covers:
                artist_covers[a_name] = s.cover_url

    # 3. Sync 'songs' index in batches
    print(f"\n[3/4] Indexing {len(song_documents)} songs into Meilisearch 'songs' index...")

    songs_index = client.index("songs")
    songs_index.update_searchable_attributes(["song_name", "artist_name"])
    songs_index.update_filterable_attributes(["artist_name"])

    BATCH_SIZE = 1000
    for i in range(0, len(song_documents), BATCH_SIZE):
        batch = song_documents[i:i + BATCH_SIZE]
        task = songs_index.add_documents(batch)
        print(f"      Batch {i//BATCH_SIZE + 1} ({len(batch)} songs) sent. Task ID: {task.task_uid}")

    # 4. Sync 'artists' index
    print(f"\n[4/4] Indexing {len(artist_counts)} unique artists into Meilisearch 'artists' index...")

    artist_documents = []
    for a_name, count in artist_counts.items():
        art_id = _artist_id(a_name)
        if art_id:
            artist_documents.append({
                "id": art_id,
                "artist_name": a_name,
                "song_count": count,
                "cover_url": artist_covers.get(a_name),
            })

    artists_index = client.index("artists")
    artists_index.update_searchable_attributes(["artist_name"])
    artists_index.update_filterable_attributes(["artist_name", "song_count"])

    for i in range(0, len(artist_documents), BATCH_SIZE):
        batch = artist_documents[i:i + BATCH_SIZE]
        task = artists_index.add_documents(batch)
        print(f"      Artist Batch {i//BATCH_SIZE + 1} ({len(batch)} artists) sent. Task ID: {task.task_uid}")

    db.close()

    print(f"\n{'='*75}")
    print("  MEILISEARCH SYNC TRIGGERED SUCCESSFULLY!")
    print(f"  Total Songs Synced   : {total_songs}")
    print(f"  Total Artists Synced : {len(artist_documents)}")
    print(f"{'='*75}\n")


if __name__ == "__main__":
    sync_all_to_meili()
