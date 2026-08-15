from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict

from app.core.database import get_db
from app.models.song import Song
from app.schemas.song_schema import SongResponse

router = APIRouter()


@router.get("/")
def get_artists(
    limit: int = Query(100, ge=1, le=500, description="Number of artists to return per page"),
    skip: int = Query(0, ge=0, description="Number of artists to skip (for pagination)"),
    search: str = Query("", description="Filter artists by name — uses Meilisearch when non-empty"),
    db: Session = Depends(get_db)
):
    """
    Retrieve artists with their song counts.

    - When `search` is provided: queries the Meilisearch 'artists' index for
      typo-tolerant, instant results (no pagination applied on search).
    - When `search` is empty: returns a paginated list sorted by song count
      from PostgreSQL.
    """
    if search and search.strip():
        # ── Meilisearch path ──────────────────────────────────────────────
        try:
            from app.services.search import get_artists_index
            index = get_artists_index()
            results = index.search(
                search.strip(),
                {
                    "limit": limit,
                    "offset": skip,
                    "sort": ["song_count:desc"],
                }
            )
            hits = results.get("hits", [])
            return [
                {"artist_name": hit["artist_name"], "song_count": hit["song_count"]}
                for hit in hits
            ]
        except Exception as e:
            print(f"[Meilisearch] Artist search failed, falling back to DB: {e}")
            # Fall through to DB path below
            rows = (
                db.query(Song.artist_name, func.count(Song.id).label("song_count"))
                .group_by(Song.artist_name)
                .filter(Song.artist_name.ilike(f"%{search.strip()}%"))
                .order_by(func.count(Song.id).desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            return [{"artist_name": row[0], "song_count": row[1]} for row in rows]

    # ── PostgreSQL pagination path ─────────────────────────────────────────
    rows = (
        db.query(Song.artist_name, func.count(Song.id).label("song_count"))
        .group_by(Song.artist_name)
        .order_by(func.count(Song.id).desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [{"artist_name": row[0], "song_count": row[1]} for row in rows]


@router.get("/{artist_name}/songs", response_model=List[SongResponse])
def get_songs_by_artist(
    artist_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    """
    Retrieve all songs by a specific artist.
    """
    songs = (
        db.query(Song)
        .filter(Song.artist_name.ilike(artist_name))
        .offset(skip)
        .limit(limit)
        .all()
    )

    if not songs:
        raise HTTPException(status_code=404, detail="Artist or songs not found")

    return songs
