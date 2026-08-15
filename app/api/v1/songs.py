from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.song import Song
from app.schemas.song_schema import SongResponse

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

@router.get("/{song_id}", response_model=SongResponse)
def get_song(song_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve a specific song by its UUID.
    """
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song
