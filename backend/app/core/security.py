import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from app.core.config import settings

# Password hashing context strictly using Argon2 as mandated
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
)


class TokenPayload(BaseModel):
    """Decoded JWT claims payload structure."""
    sub: str  # User UUID string
    email: Optional[str] = None
    exp: Optional[int] = None
    type: str = "access"  # "access" or "refresh"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against an Argon2 hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Computes a cryptographically secure Argon2 password hash."""
    return pwd_context.hash(password)


hash_password = get_password_hash


def hash_token(raw_token: str) -> str:
    """
    Computes a deterministic SHA-256 hash of a raw token for secure database storage.
    Ensures raw refresh tokens are never stored in plain text.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_secure_token(n_bytes: int = 48) -> str:
    """Generates a high-entropy cryptographically secure random token string."""
    return secrets.token_urlsafe(n_bytes)


def create_access_token(
    subject: Optional[Union[str, Any]] = None,
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    user_id: Optional[Union[str, Any]] = None,
) -> str:
    """Generates an encoded HS256 JWT access token."""
    actual_sub = subject if subject is not None else user_id
    if actual_sub is None:
        raise ValueError("Subject or user_id is required to create access token.")
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(actual_sub),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: Optional[Union[str, Any]] = None,
    email: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
    user_id: Optional[Union[str, Any]] = None,
) -> str:
    actual_sub = subject if subject is not None else user_id
    if actual_sub is None:
        raise ValueError("Subject or user_id is required to create refresh token.")
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode: Dict[str, Any] = {
        "sub": str(actual_sub),
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT access token against secret key, algorithm, and expiration."""
    from jose.exceptions import ExpiredSignatureError, JWTError
    from app.core.exceptions import AuthenticationException
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise AuthenticationException("Authentication token has expired.")
    except (JWTError, Exception):
        raise AuthenticationException("Invalid or tampered authentication token.")


def decode_token(token: str) -> Optional[TokenPayload]:
    """Decodes and validates a JWT token against secret key, algorithm, and expiration."""
    try:
        payload = decode_access_token(token)
        return TokenPayload(**payload)
    except Exception:
        return None
