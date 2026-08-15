from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

from app.core.database import get_db
from app.models.user import User
from app.models.device_token import DeviceToken
from app.services.auth import get_current_user

router = APIRouter()

class DeviceRegister(BaseModel):
    fcm_token: str
    platform: str = "unknown"

@router.post("/register")
def register_device(
    body: DeviceRegister,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Registers an FCM device token for the current user.
    If the token already exists, it updates the user_id and last_seen.
    """
    token_record = db.query(DeviceToken).filter(DeviceToken.fcm_token == body.fcm_token).first()
    
    if token_record:
        # Token exists, update it (maybe user switched accounts on same device)
        token_record.user_id = current_user.id
        token_record.platform = body.platform
        token_record.is_active = True
        token_record.last_seen = datetime.now(timezone.utc)
    else:
        # Create new token record
        token_record = DeviceToken(
            user_id=current_user.id,
            fcm_token=body.fcm_token,
            platform=body.platform,
        )
        db.add(token_record)
        
    db.commit()
    return {"status": "success", "detail": "Device registered for push notifications."}

@router.delete("/{fcm_token}")
def unregister_device(
    fcm_token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Removes a device token when the user logs out.
    """
    token_record = db.query(DeviceToken).filter(
        DeviceToken.fcm_token == fcm_token,
        DeviceToken.user_id == current_user.id
    ).first()
    
    if token_record:
        db.delete(token_record)
        db.commit()
        
    return {"status": "success", "detail": "Device unregistered."}
