import re
import meilisearch
from app.core.config import settings


def get_meilisearch_client():
    """
    Returns an authenticated Meilisearch client instance.
    """
    return meilisearch.Client(settings.MEILI_URL, settings.MEILI_MASTER_KEY)


def get_songs_index():
    """
    Returns the Meilisearch 'songs' index.
    """
    return get_meilisearch_client().index("songs")


def get_artists_index():
    """
    Returns the Meilisearch 'artists' index.
    """
    return get_meilisearch_client().index("artists")


def _artist_id(artist_name: str) -> str:
    """
    Converts an artist name to a stable, URL-safe document ID for Meilisearch.
    e.g. "Indrachapa Liyanage" -> "indrachapa_liyanage"
    """
    return re.sub(r'[^a-z0-9]+', '_', artist_name.strip().lower()).strip('_')


def sync_artist_to_meili(db, artist_name: str) -> None:
    """
    Recalculates the song count for `artist_name` from the database and
    upserts the artist document into the Meilisearch 'artists' index.
    Called after any song insert / update / delete.
    """
    try:
        from sqlalchemy import func
        from app.models.song import Song

        song_count = (
            db.query(func.count(Song.id))
            .filter(Song.artist_name == artist_name)
            .scalar()
        ) or 0

        index = get_artists_index()

        if song_count == 0:
            # No songs left — remove this artist from the index
            index.delete_document(_artist_id(artist_name))
        else:
            index.add_documents([{
                "id": _artist_id(artist_name),
                "artist_name": artist_name,
                "song_count": song_count,
            }])
    except Exception as e:
        print(f"[Meilisearch] Failed to sync artist '{artist_name}': {e}")


def ensure_artists_index_settings() -> None:
    """
    Configures the 'artists' Meilisearch index with correct searchable attributes
    and ranking rules. Safe to call multiple times (idempotent).
    """
    try:
        index = get_artists_index()
        index.update_searchable_attributes(["artist_name"])
        index.update_sortable_attributes(["song_count", "artist_name"])
        index.update_ranking_rules([
            "words",
            "typo",
            "proximity",
            "attribute",
            "sort",
            "exactness",
        ])
        print("[Meilisearch] 'artists' index settings applied.")
    except Exception as e:
        print(f"[Meilisearch] Failed to apply artists index settings: {e}")
