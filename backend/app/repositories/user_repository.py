import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import User, RefreshToken


class UserRepository:
    """
    Database repository handling user persistence, credential verification,
    and refresh token rotation with cryptographic hashes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str) -> Optional[User]:
        """Looks up a user by email address (case-insensitive)."""
        stmt = select(User).where(User.email.ilike(email.strip()))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Looks up a user by their UUID primary key."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create(self, full_name: str, email: str, password_hash: str) -> User:
        """Creates a new active user record."""
        user = User(
            full_name=full_name.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            is_active=True,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def store_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Persists the SHA-256 hash of an issued refresh token."""
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_valid_refresh_token(self, token_hash: str) -> Optional[RefreshToken]:
        """
        Retrieves a refresh token record only if it is active, unrevoked, and unexpired.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def revoke_refresh_token(self, token_hash: str) -> bool:
        """Marks a refresh token as revoked (used in token rotation and logout)."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        """Revokes all active refresh tokens for a user (e.g., password reset / account lock)."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount
