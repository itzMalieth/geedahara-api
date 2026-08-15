from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from uuid import UUID
import random

from app.core.database import get_db
from app.models.song import Song
from app.models.playlist import Playlist
from app.models.user import User
from app.schemas.song_schema import SongResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/trending", response_model=List[SongResponse])
def get_trending_songs(limit: int = 20, db: Session = Depends(get_db)):
    """
    Returns the most played songs across the entire app.
    """
    trending = db.query(Song).order_by(Song.play_count.desc()).limit(limit).all()
    return trending

@router.post("/songs/{song_id}/play")
def record_song_play(song_id: UUID, db: Session = Depends(get_db)):
    """
    Increments the play_count for a specific song.
    """
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
        
    song.play_count += 1
    db.commit()
    return {"message": "Play recorded", "new_play_count": song.play_count}

@router.get("/for-me", response_model=List[SongResponse])
def get_personalized_recommendations(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns personalized recommendations by analyzing the artists in the user's playlists.
    Mixes in a few random songs for discovery.
    """
    # 1. Get all playlists for the user
    playlists = db.query(Playlist).filter(Playlist.user_id == current_user.id).all()
    
    # 2. Extract favorite artists
    favorite_artists = set()
    for playlist in playlists:
        for song in playlist.songs:
            favorite_artists.add(song.artist_name)
            
    recommendations = []
    
    # 3. If they have favorite artists, fetch some songs by them
    if favorite_artists:
        recommended_artist_songs = (
            db.query(Song)
            .filter(Song.artist_name.in_(favorite_artists))
            .order_by(func.random())
            .limit(limit // 2)
            .all()
        )
        recommendations.extend(recommended_artist_songs)
        
    # 4. Fill the rest of the limit with random Discovery songs
    remaining_limit = limit - len(recommendations)
    if remaining_limit > 0:
        random_songs = db.query(Song).order_by(func.random()).limit(remaining_limit).all()
        # Avoid duplicates
        for r_song in random_songs:
            if r_song not in recommendations:
                recommendations.append(r_song)
                
    # Shuffle the final mix
    random.shuffle(recommendations)
    return recommendations
