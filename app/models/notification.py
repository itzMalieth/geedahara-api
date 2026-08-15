from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from datetime import datetime, timezone
import uuid

class Notification(Base):
    """
    Persistent notification history for the in-app Bell screen.
    We broadcast these to all users, so there is no user_id FK here.
    """
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    
    # E.g., 'song', 'app_update', 'announcement'
    type = Column(String(100), nullable=True)
    
    # ID of the related entity for deep linking (e.g., song ID)
    reference_id = Column(String(255), nullable=True)
    
    image_url = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
