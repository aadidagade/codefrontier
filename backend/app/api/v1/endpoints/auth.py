from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.database import get_db
from app.dependencies.auth import get_current_user
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.common import ApiResponse
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    LogoutRequest,
    AuthResponse,
    UserResponse,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=ApiResponse[AuthResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=5, window_seconds=60))],
    summary="Register Team Member Account",
    description="Registers a new team member with Argon2 password hashing and issues an initial authenticated session.",
)
async def register(
    req: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    result = await auth_service.register(req)
    return ApiResponse(
        data=result,
        message="Account registered successfully. Session initialized.",
    )


@router.post(
    "/login",
    response_model=ApiResponse[AuthResponse],
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))],
    summary="User Login",
    description="Authenticates team member credentials using Argon2 and issues short-lived JWT access token and refresh token.",
)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    result = await auth_service.login(credentials)
    return ApiResponse(
        data=result,
        message="Authentication successful.",
    )


@router.post(
    "/refresh",
    response_model=ApiResponse[AuthResponse],
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
    summary="Refresh Access Token (Token Rotation)",
    description="Validates and revokes the submitted refresh token, issuing a fresh access token and a new rotated refresh token.",
)
async def refresh_token(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    result = await auth_service.refresh_token(req.refresh_token)
    return ApiResponse(
        data=result,
        message="Token session rotated successfully.",
    )


@router.post(
    "/logout",
    response_model=ApiResponse[bool],
    summary="User Logout & Token Revocation",
    description="Revokes the submitted refresh token, invalidating the session in the database.",
)
async def logout(
    req: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    auth_service = AuthService(db)
    await auth_service.logout(req.refresh_token)
    return ApiResponse(
        data=True,
        message="Session revoked and logged out successfully.",
    )


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="Current User Profile",
    description="Retrieves the authenticated team member's active profile.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return ApiResponse(
        data=UserResponse.model_validate(current_user),
        message="Current user profile retrieved.",
    )
