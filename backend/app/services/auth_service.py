import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    generate_secure_token,
    hash_token,
)
from app.core.exceptions import (
    ConflictException,
    UnauthorizedException,
    NotFoundException,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    AuthResponse,
    UserResponse,
)


class AuthService:
    """
    Business service executing authentication workflows, Argon2 verification,
    JWT access token issuance, and refresh token rotation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def _issue_token_package(self, user: User) -> AuthResponse:
        """Helper to generate an access token and rotated refresh token."""
        # 1. Generate short-lived JWT Access Token
        access_token = create_access_token(
            subject=user.id,
            email=user.email,
        )

        # 2. Generate high-entropy Refresh Token
        raw_refresh_token = generate_secure_token(48)
        token_hash = hash_token(raw_refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        # 3. Store hash in database
        await self.user_repo.store_refresh_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        return AuthResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse.model_validate(user),
        )

    async def register(self, req: RegisterRequest) -> AuthResponse:
        """Registers a new user account with duplicate prevention and Argon2 hashing."""
        # 1. Check for duplicate email
        existing_user = await self.user_repo.get_by_email(req.email)
        if existing_user:
            raise ConflictException(
                message=f"A user with email '{req.email}' is already registered.",
                details={"email": req.email},
            )

        # 2. Hash password with Argon2
        hashed_pw = get_password_hash(req.password)

        # 3. Create user record
        user = await self.user_repo.create(
            full_name=req.full_name,
            email=req.email,
            password_hash=hashed_pw,
        )

        # 4. Issue authenticated session
        return await self._issue_token_package(user)

    async def login(self, req: LoginRequest) -> AuthResponse:
        """Authenticates user credentials and issues a session."""
        user = await self.user_repo.get_by_email(req.email)
        if not user or not user.is_active:
            raise UnauthorizedException("Invalid email address or password.")

        if not verify_password(req.password, user.password_hash):
            raise UnauthorizedException("Invalid email address or password.")

        return await self._issue_token_package(user)

    async def refresh_token(self, raw_refresh_token: str) -> AuthResponse:
        """
        Rotates an existing refresh token:
        1. Validates and revokes the existing refresh token.
        2. Issues a brand-new access token and refresh token.
        """
        token_hash = hash_token(raw_refresh_token)
        record = await self.user_repo.get_valid_refresh_token(token_hash)
        if not record:
            raise UnauthorizedException("Refresh token is invalid, expired, or has been revoked.")

        user = await self.user_repo.get_by_id(record.user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("Associated user account is deactivated or no longer exists.")

        # Revoke old refresh token (Token Rotation guarantee)
        await self.user_repo.revoke_refresh_token(token_hash)

        # Issue fresh token package
        return await self._issue_token_package(user)

    async def logout(self, raw_refresh_token: Optional[str]) -> bool:
        """Revokes the specified refresh token to securely terminate session."""
        if not raw_refresh_token:
            return True

        token_hash = hash_token(raw_refresh_token)
        return await self.user_repo.revoke_refresh_token(token_hash)
