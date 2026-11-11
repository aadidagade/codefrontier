import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload for registering a new team member account."""
    full_name: str = Field(..., min_length=2, max_length=255, description="Member full legal or display name")
    email: EmailStr = Field(..., description="Valid company/team email address")
    password: str = Field(..., min_length=8, max_length=128, description="Strong password (min 8 chars)")


class LoginRequest(BaseModel):
    """Payload for user authentication."""
    email: EmailStr = Field(..., description="Account email address")
    password: str = Field(..., min_length=1, description="Account password")


class RefreshTokenRequest(BaseModel):
    """Payload for issuing a new access token via refresh token."""
    refresh_token: str = Field(..., min_length=10, description="Raw refresh token issued at login")


class LogoutRequest(BaseModel):
    """Payload for terminating active session and revoking token."""
    refresh_token: Optional[str] = Field(None, description="Refresh token to revoke")


class UserResponse(BaseModel):
    """Safe user profile response representation (never exposes password hash)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    profile_image: Optional[str] = None
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    """Token package returned on successful login, registration, or refresh."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserResponse
