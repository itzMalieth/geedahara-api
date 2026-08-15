"""
HelaGee Auth Router — Phase 2

Endpoints:
  POST /auth/google    — Google OIDC → issue token pair (rate-limited: 5/min per IP)
  POST /auth/refresh   — Rotate refresh token → new token pair
  POST /auth/logout    — Revoke current session
  POST /register       — Email/password register (future use)
  POST /login          — Email/password login (future use)
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth_schema import (
    GoogleLoginRequest,
    RefreshTokenRequest,
    UserRegister,
    TokenPairResponse,
    TokenResponse,
)
from app.services.auth import (
    verify_google_token,
    create_access_token,
    get_password_hash,
    verify_password,
    get_current_user,
    generate_refresh_token,
    hash_refresh_token,
    refresh_token_expiry,
)
import uuid
from datetime import datetime, timezone

router = APIRouter()

# ---------------------------------------------------------------------------
# Rate limiter — keyed by client IP
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# Internal helper — create a full session (access + refresh token pair)
# ---------------------------------------------------------------------------

def _create_token_pair(user: User, db: Session, device_info: str = None, platform: str = None) -> TokenPairResponse:
    """
    Generates a new access + refresh token pair for the given user.
    Saves the hashed refresh token to user_sessions table.
    Returns TokenPairResponse.
    """
    # 1. Generate tokens
    access_token = create_access_token(str(user.id))
    raw_refresh_token = generate_refresh_token()
    token_hash = hash_refresh_token(raw_refresh_token)
    expires = refresh_token_expiry()

    # 2. Persist session (hashed refresh token only)
    session = UserSession(
        id=uuid.uuid4(),
        user_id=user.id,
        refresh_token_hash=token_hash,
        device_info=device_info,
        platform=platform,
        expires_at=expires,
    )
    db.add(session)
    db.commit()

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,  # raw token sent once — never stored raw
        expires_in=15 * 60,               # 15 minutes in seconds
    )


# ---------------------------------------------------------------------------
# Google OIDC Auth
# ---------------------------------------------------------------------------

@router.post("/google", response_model=TokenPairResponse)
@limiter.limit("5/minute")
def google_auth(request: Request, body: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Validates Google ID Token from Flutter, finds/creates HelaGee user,
    returns a short-lived access token + long-lived refresh token.

    Rate limited: 5 requests per minute per IP address.

    Security:
      - Identity keyed on google_sub (stable OIDC sub claim, not email)
      - email_verified enforced
      - Race-safe user creation (IntegrityError catch)
      - Refresh token stored as SHA-256 hash (never raw)
    """
    # 1. Verify Google ID Token
    google_user_info = verify_google_token(body.id_token)

    google_sub = google_user_info.get("sub")
    email      = google_user_info.get("email")
    name       = google_user_info.get("name") or email
    picture    = google_user_info.get("picture")

    if not google_sub or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incomplete Google profile data",
        )

    # 2. Find user by google_sub (primary identity — not email)
    user = db.query(User).filter(User.google_sub == google_sub).first()

    # 3. Race-safe first-time account creation
    if not user:
        try:
            user = User(
                id=uuid.uuid4(),
                email=email,
                name=name,
                google_sub=google_sub,
                profile_picture=picture,
                role="user",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError:
            db.rollback()
            user = db.query(User).filter(User.google_sub == google_sub).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="User creation failed. Please try again.",
                )

    # 4. Issue token pair + create session
    # Extract optional device info from request headers (Flutter can send these)
    device_info = request.headers.get("X-Device-Info")
    platform    = request.headers.get("X-Platform")

    return _create_token_pair(user, db, device_info=device_info, platform=platform)


# ---------------------------------------------------------------------------
# Refresh Token — issues new token pair + rotates refresh token
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=TokenPairResponse)
def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access + refresh token pair.

    Refresh token rotation:
      - Incoming refresh token is validated against user_sessions table
      - The matching session row is revoked (revoked_at set)
      - A new session row is created with a new refresh token hash
      - The old raw refresh token is now invalid

    Raises HTTP 401 if token is invalid, expired, or already revoked.
    """
    token_hash = hash_refresh_token(body.refresh_token)

    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == token_hash
    ).first()

    # Validate the session
    if not session or not session.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or has expired. Please sign in again.",
        )

    # Load user
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    # Revoke old session (rotation — the old refresh token is now dead)
    session.revoked_at = datetime.now(timezone.utc)
    db.commit()

    # Issue new token pair
    return _create_token_pair(
        user, db,
        device_info=session.device_info,
        platform=session.platform,
    )


# ---------------------------------------------------------------------------
# Logout — revoke current session
# ---------------------------------------------------------------------------

@router.post("/logout")
def logout(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Revokes the provided refresh token session.
    Client MUST delete both access_token and refresh_token from secure storage.

    Accepts the refresh_token in the body so we can revoke the exact session.
    (Access token will naturally expire after 15 minutes even without revocation.)
    """
    token_hash = hash_refresh_token(body.refresh_token)

    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == token_hash
    ).first()

    if session and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        db.commit()

    # Always return 200 — don't leak whether the token existed
    return {"detail": "Logged out successfully"}


# ---------------------------------------------------------------------------
# Account Deletion — Soft delete current user
# ---------------------------------------------------------------------------

@router.delete("/me")
def delete_my_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Soft deletes the current user's account by setting deleted_at to now.
    Revokes ALL active sessions for this user.
    """
    # 1. Soft delete user
    current_user.deleted_at = datetime.now(timezone.utc)
    
    # 2. Revoke all active sessions
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.revoked_at == None
    ).all()
    for session in sessions:
        session.revoked_at = datetime.now(timezone.utc)
        
    db.commit()
    return {"detail": "Account deleted successfully. Sorry to see you go!"}


# ---------------------------------------------------------------------------
# Email / Password Auth (kept for future use)
# ---------------------------------------------------------------------------


from fastapi.security import OAuth2PasswordRequestForm

@router.post("/register", response_model=TokenResponse)
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register with email/password (future use — currently Google-only in Flutter)."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        id=uuid.uuid4(),
        email=user_data.email,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return TokenResponse(access_token=create_access_token(str(new_user.id)))


@router.post("/login", response_model=TokenResponse)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email/password (future use)."""
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    return TokenResponse(access_token=create_access_token(str(user.id)))
