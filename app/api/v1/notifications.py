from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.notification import Notification
from app.services.auth import get_current_user, require_admin
from app.services.fcm import send_topic_notification

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NotificationCreate(BaseModel):
    title: str
    body: str
    type: Optional[str] = None
    reference_id: Optional[str] = None
    image_url: Optional[str] = None

class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    type: Optional[str]
    reference_id: Optional[str]
    image_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    limit: int = 20,
    skip: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the history of notifications. This powers the in-app Bell screen.
    """
    notifications = db.query(Notification).order_by(
        Notification.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    # We convert UUID to string for the response
    for n in notifications:
        n.id = str(n.id)
        
    return notifications


@router.post("/admin", response_model=NotificationResponse)
def create_and_broadcast_notification(
    body: NotificationCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    ADMIN ONLY:
    1. Saves the notification to the DB.
    2. Broadcasts it via FCM to the 'helaGee_all_users' topic.
    """
    # 1. Save to database
    notification = Notification(
        title=body.title,
        body=body.body,
        type=body.type,
        reference_id=body.reference_id,
        image_url=body.image_url
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # 2. Build data payload for Flutter deep linking
    data_payload = {}
    if body.type:
        data_payload['type'] = body.type
    if body.reference_id:
        data_payload['reference_id'] = body.reference_id
        
    # 3. Broadcast to all users via FCM topic
    send_topic_notification(
        topic="helaGee_all_users",
        title=body.title,
        body=body.body,
        data=data_payload
    )
    
    notification.id = str(notification.id)
    return notification
