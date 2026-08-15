from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.song import Song
from app.schemas.song_schema import SongResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/songs/{song_id}")
def toggle_favorite_song(
    song_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Toggles a song in the user's favorites list.
    If the song is already favorited, it removes it (un-likes).
    If it's not favorited, it adds it (likes).
    """
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Check if it's already a favorite
    if song in current_user.favorite_songs:
        current_user.favorite_songs.remove(song)
        db.commit()
        return {"status": "removed", "message": "Song removed from favorites"}
    else:
        current_user.favorite_songs.append(song)
        db.commit()
        return {"status": "added", "message": "Song added to favorites"}

@router.get("/songs", response_model=List[SongResponse])
def get_favorite_songs(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns a paginated list of all the user's liked songs.
    """
    favorite_songs = current_user.favorite_songs.limit(limit).offset(offset).all()
    return favorite_songs
