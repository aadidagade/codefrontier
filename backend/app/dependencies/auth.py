import uuid
from typing import Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import decode_token, TokenPayload
from app.core.exceptions import UnauthorizedException
from app.dependencies.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_token_payload(
    token: Optional[str] = Depends(oauth2_scheme),
) -> TokenPayload:
    """Validates the incoming Authorization: Bearer JWT token."""
    if not token:
        raise UnauthorizedException("Authentication token is required.")

    payload = decode_token(token)
    if not payload or payload.type != "access":
        raise UnauthorizedException("Invalid, expired, or malformed authentication token.")

    return payload


async def get_current_user(
    payload: TokenPayload = Depends(get_current_token_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency returning the currently authenticated, active User record from PostgreSQL.
    """
    try:
        user_uuid = uuid.UUID(payload.sub)
    except (ValueError, TypeError):
        raise UnauthorizedException("Invalid token subject format.")

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_uuid)
    if not user:
        raise UnauthorizedException("Authenticated user not found.")

    if not user.is_active:
        raise UnauthorizedException("User account has been deactivated.")

    return user
