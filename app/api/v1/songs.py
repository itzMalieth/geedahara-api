from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.song import Song
from app.schemas.song_schema import SongResponse, SyncLyricsRequest

router = APIRouter()

@router.get("/", response_model=List[SongResponse])
def get_songs(
    skip: int = Query(0, ge=0, description="Skip N records (Pagination)"),
    limit: int = Query(1000, ge=1, le=10000, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve a paginated list of songs (supports up to 10,000 songs per request).
    """
    songs = db.query(Song).offset(skip).limit(limit).all()
    return songs


@router.get("/with-lyrics", response_model=List[SongResponse])
def get_songs_with_lyrics(
    type: str = Query("all", description="Lyrics type filter: 'all', 'lrc' (synced only), 'full' (plain text/json only)"),
    sort: str = Query("recent", description="Sort order: 'recent' (newest lyrics first), 'popular' (most plays), 'name' (alphabetical)"),
    skip: int = Query(0, ge=0, description="Skip N records (Pagination)"),
    limit: int = Query(20, ge=1, le=100, description="Number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve songs that have verified lyrics in Cloudflare R2.
    Supports filtering by LRC synced vs full text lyrics and sorting by newest added lyrics.
    """
    query = db.query(Song)

    # 1. Filter by lyrics type
    if type == "lrc":
        query = query.filter(Song.has_lrc == True)
    elif type == "full":
        query = query.filter(Song.has_full_lyrics == True)
    else:
        query = query.filter(or_(Song.has_lrc == True, Song.has_full_lyrics == True))

    # 2. Sort order
    if sort == "recent":
        query = query.order_by(
            Song.lyrics_updated_at.desc().nullslast(),
            Song.created_at.desc()
        )
    elif sort == "popular":
        query = query.order_by(Song.play_count.desc())
    elif sort == "name":
        query = query.order_by(Song.song_name.asc())

    songs = query.offset(skip).limit(limit).all()
    return songs


@router.post("/sync-lyrics", response_model=SongResponse)
def sync_song_lyrics(
    payload: SyncLyricsRequest,
    db: Session = Depends(get_db)
):
    """
    Ingestion/Webhook endpoint to update lyrics status for a song when created/modified.
    Used by lrc-generator and synchronization scripts.
    """
    song = None

    if payload.song_id:
        song = db.query(Song).filter(Song.id == payload.song_id).first()

    if not song and payload.folder_name:
        # Match by r2_folder or URL substring
        folder_clean = payload.folder_name.strip()
        song = db.query(Song).filter(
            or_(
                Song.r2_folder == folder_clean,
                Song.original_music_link.ilike(f"%/{folder_clean}/%")
            )
        ).first()

    if not song and payload.song_name:
        song = db.query(Song).filter(Song.song_name.ilike(payload.song_name.strip())).first()

    if not song:
        raise HTTPException(
            status_code=404,
            detail=f"Song not found for given criteria (folder: {payload.folder_name}, id: {payload.song_id})"
        )

    # Update metadata
    if payload.has_lrc is not None:
        song.has_lrc = payload.has_lrc
    if payload.r2_lrc_link:
        song.r2_lrc_link = payload.r2_lrc_link

    if payload.has_full_lyrics is not None:
        song.has_full_lyrics = payload.has_full_lyrics
    if payload.full_lyrics_format:
        song.full_lyrics_format = payload.full_lyrics_format
    if payload.r2_full_lyrics_link:
        song.r2_full_lyrics_link = payload.r2_full_lyrics_link

    if payload.folder_name and not song.r2_folder:
        song.r2_folder = payload.folder_name.strip()

    song.lyrics_updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(song)
    return song


@router.get("/{song_id}", response_model=SongResponse)
def get_song(song_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve a specific song by its UUID.
    """
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song
