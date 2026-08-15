from pydantic import BaseModel
from typing import Optional


class GoogleLoginRequest(BaseModel):
    id_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserRegister(BaseModel):
    email: str
    name: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    """Legacy single-token response — kept for backwards compatibility."""
    access_token: str
    token_type: str = "bearer"


class TokenPairResponse(BaseModel):
    """
    Phase 2: Full token pair response returned by /auth/google and /auth/refresh.

    access_token:  Short-lived JWT (15 minutes). Use for all API Bearer headers.
    refresh_token: Long-lived opaque token (30 days). Use ONLY for /auth/refresh.
    expires_in:    Access token lifetime in seconds (900 = 15 minutes).
    token_type:    Always "bearer".
    """
    access_token: str
    refresh_token: str
    expires_in: int = 900    # 15 * 60 seconds
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    profile_picture: Optional[str] = None
    role: str = "user"

    class Config:
        from_attributes = True
