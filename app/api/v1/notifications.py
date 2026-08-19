from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
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
    type: Optional[str] = "announcement"
    reference_id: Optional[str] = None
    image_url: Optional[str] = None

class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    type: Optional[str] = None
    reference_id: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    limit: int = 20,
    skip: int = 0,
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
    request: Request,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    db: Session = Depends(get_db)
):
    """
    ADMIN ONLY:
    1. Saves the notification to the DB.
    2. Broadcasts it via FCM to the 'helaGee_all_users' topic.

    Authenticate via:
      - Header 'X-Admin-Key: <secret_key>' (e.g. JWT_SECRET_KEY or 'helagee_admin_secret_2026')
      - OR Bearer JWT Token with role='admin'
    """
    # 1. Check API Secret Key
    valid_keys = {
        settings.JWT_SECRET_KEY,
        settings.URL_SIGNING_SECRET,
        "helagee_admin_secret_2026",
        "geerasa_admin_secret_2026",
    }
    
    is_authenticated = False
    if x_admin_key and x_admin_key in valid_keys:
        is_authenticated = True
    else:
        # Check Bearer JWT or Admin Key in Bearer field
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            if token in valid_keys:
                is_authenticated = True
            else:
                try:
                    import jwt
                    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                    user_id = payload.get("sub")
                    user = db.query(User).filter(User.id == user_id).first()
                    if user and user.role == "admin":
                        is_authenticated = True
                except Exception:
                    pass

    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required. Click Authorize and enter 'geerasa_admin_secret_2026' or admin JWT.",
        )

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
    if body.image_url:
        data_payload['image_url'] = body.image_url
        
    # 3. Broadcast to all users via FCM topic
    send_topic_notification(
        topic="helaGee_all_users",
        title=body.title,
        body=body.body,
        data=data_payload,
        image_url=body.image_url
    )
    
    notification.id = str(notification.id)
    return notification
