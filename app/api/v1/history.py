from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.song import Song
from app.models.history import ListeningHistory
from app.schemas.song_schema import SongResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/songs/{song_id}")
def record_listening_history(
    song_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Records that the authenticated user just played this song.
    """
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    history_record = ListeningHistory(
        user_id=current_user.id,
        song_id=song.id
    )
    db.add(history_record)
    db.commit()
    
    return {"status": "success", "message": "Listening history recorded"}

@router.get("/", response_model=List[SongResponse])
def get_recently_played_songs(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns the user's recently played songs, most recent first.
    Filters out duplicates so each song only appears once in the recent list.
    """
    # Fetch the last 100 history records
    history_records = (
        db.query(ListeningHistory)
        .filter(ListeningHistory.user_id == current_user.id)
        .order_by(ListeningHistory.played_at.desc())
        .limit(100)
        .all()
    )
    
    # Extract unique songs maintaining chronological order
    unique_songs = []
    seen_song_ids = set()
    
    for record in history_records:
        if record.song_id not in seen_song_ids:
            seen_song_ids.add(record.song_id)
            unique_songs.append(record.song)
            if len(unique_songs) >= limit:
                break
                
    return unique_songs
