from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.song import Song
from app.models.playlist import Playlist
from app.schemas.playlist_schema import PlaylistCreate, PlaylistResponse, PlaylistAddSong
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=PlaylistResponse)
def create_playlist(
    playlist_in: PlaylistCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new empty playlist for the authenticated user.
    """
    new_playlist = Playlist(
        name=playlist_in.name,
        user_id=current_user.id
    )
    db.add(new_playlist)
    db.commit()
    db.refresh(new_playlist)
    return new_playlist

@router.get("/me", response_model=List[PlaylistResponse])
def get_my_playlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all playlists owned by the authenticated user.
    """
    playlists = db.query(Playlist).filter(Playlist.user_id == current_user.id).all()
    return playlists

@router.get("/{playlist_id}", response_model=PlaylistResponse)
def get_playlist(
    playlist_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific playlist and its songs. Must be owned by the user.
    """
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == current_user.id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist

@router.post("/{playlist_id}/songs", response_model=PlaylistResponse)
def add_song_to_playlist(
    playlist_id: UUID,
    song_data: PlaylistAddSong,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a song to a specific playlist.
    """
    # 1. Verify the playlist exists and belongs to the user
    playlist = db.query(Playlist).filter(Playlist.id == playlist_id, Playlist.user_id == current_user.id).first()
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    # 2. Verify the song exists
    song = db.query(Song).filter(Song.id == song_data.song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
        
    # 3. Check if song is already in playlist to avoid duplicates
    if song in playlist.songs:
        raise HTTPException(status_code=400, detail="Song is already in this playlist")
        
    # 4. Add the song
    playlist.songs.append(song)
    db.commit()
    db.refresh(playlist)
    
    return playlist
