"""
HelaGee Auth Services — Phase 2
Handles:
  - Access token creation (15 min)
  - Refresh token generation + hashing + rotation
  - Google OIDC verification (with email_verified check)
  - get_current_user() dependency for protected routes
"""

import jwt
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings

import bcrypt

# ---------------------------------------------------------------------------
# Password helpers (kept for future email/password auth)
# ---------------------------------------------------------------------------

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


# ---------------------------------------------------------------------------
# Access Token (short-lived, 15 minutes)
# ---------------------------------------------------------------------------

def create_access_token(user_id: str) -> str:
    """
    Creates a short-lived signed JWT (15 min).
    Payload: {"sub": user_id, "exp": ...}
    JWT is signed, NOT encrypted — keep payload minimal.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRY_MINUTES
    )
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Refresh Token (long-lived, 30 days — stored as hash in DB)
# ---------------------------------------------------------------------------

def generate_refresh_token() -> str:
    """Generates a cryptographically secure random 64-byte hex refresh token."""
    return secrets.token_hex(64)

def hash_refresh_token(raw_token: str) -> str:
    """Returns SHA-256 hash of the raw refresh token (what we store in DB)."""
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRY_DAYS)


# ---------------------------------------------------------------------------
# get_current_user — FastAPI Dependency for Protected Routes
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    FastAPI dependency — decodes the short-lived access JWT and returns the User.

    Usage:
        @router.get("/me")
        def get_me(current_user = Depends(get_current_user)):
            return current_user

    Returns HTTP 401 if:
      - No Bearer token provided
      - Token is invalid or tampered
      - Token is expired (client should use /auth/refresh)
      - User not found in DB
    """
    from app.models.user import User  # avoid circular import

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired. Use /auth/refresh to get a new one.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deleted. Please contact support.",
        )

    return user


def require_admin(current_user=Depends(get_current_user)):
    """
    FastAPI dependency — requires current user to have role='admin'.
    Usage:
        @router.delete("/admin/songs/{id}")
        def delete_song(current_user = Depends(require_admin)):
            ...
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user


# ---------------------------------------------------------------------------
# Google OIDC Verification
# ---------------------------------------------------------------------------

def verify_google_token(token: str) -> Dict:
    """
    Verifies a Google ID Token sent from Flutter google_sign_in.

    Checks:
      - Cryptographic signature (google-auth library)
      - Token expiry (exp)
      - Issuer (iss): must be accounts.google.com
      - Audience (aud): must match GOOGLE_CLIENT_ID
      - email_verified: must be True

    Returns verified payload dict, or raises HTTP 401.
    """
    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )

        if idinfo.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
            raise ValueError('Token issuer is invalid.')

        if not idinfo.get('email_verified', False):
            raise ValueError('Google account email is not verified.')

        return idinfo

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}",
        )
