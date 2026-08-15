from sqlalchemy import Column, String, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import uuid
from sqlalchemy.dialects.postgresql import UUID

# Junction table to link songs and playlists (Many-to-Many)
playlist_song_association = Table(
    "playlist_songs",
    Base.metadata,
    Column("playlist_id", UUID(as_uuid=True), ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True),
    Column("song_id", UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True)
)

class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    owner = relationship("User")
    songs = relationship("Song", secondary=playlist_song_association)
