from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base
from datetime import datetime, timezone
import uuid

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    refresh_token_hash = Column(String(64), nullable=False, unique=True, index=True)
    
    device_info = Column(String(255), nullable=True)
    platform = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def is_valid(self) -> bool:
        """Returns True if the session is neither revoked nor expired."""
        if self.revoked_at is not None:
            return False
        if datetime.now(timezone.utc) > self.expires_at:
            return False
        return True
