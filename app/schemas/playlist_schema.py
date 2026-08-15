from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from app.schemas.song_schema import SongResponse

class PlaylistBase(BaseModel):
    name: str

class PlaylistCreate(PlaylistBase):
    pass
    
class PlaylistAddSong(BaseModel):
    song_id: UUID

class PlaylistResponse(PlaylistBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    # List of songs included in this playlist
    songs: List[SongResponse] = []

    model_config = ConfigDict(from_attributes=True)
