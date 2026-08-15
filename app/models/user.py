from sqlalchemy import Column, String, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timezone
import uuid
from sqlalchemy.dialects.postgresql import UUID

# Junction table for Liked Songs
user_favorite_songs = Table(
    "user_favorite_songs",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("song_id", UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(320), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    profile_picture = Column(String, nullable=True)

    # Google OpenID Connect 'sub' claim — stable unique identifier per Google account
    google_sub = Column(String(255), unique=True, index=True, nullable=True)

    # Standard Email/Password Auth (Optional — kept for future use)
    hashed_password = Column(String, nullable=True)

    # User role: 'user' or 'admin'
    role = Column(String(50), nullable=False, default="user")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Soft Deletion timestamp (Phase 3)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    favorite_songs = relationship("Song", secondary=user_favorite_songs, lazy="dynamic")
