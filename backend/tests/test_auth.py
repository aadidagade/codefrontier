import pytest
from httpx import AsyncClient
from app.core.security import get_password_hash, verify_password


def test_argon2_hashing():
    """Confirms Argon2 hashing and verification."""
    password = "SuperSecurePassword123!"
    hashed = get_password_hash(password)
    assert hashed.startswith("$argon2")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.asyncio
async def test_register_validation(async_client: AsyncClient):
    """Verifies that invalid email and short password fail schema validation."""
    # 1. Invalid email
    res1 = await async_client.post(
        "/api/v1/auth/register",
        json={"full_name": "Alice", "email": "not-an-email", "password": "Password123!"},
    )
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "VALIDATION_ERROR"

    # 2. Short password (< 8 chars)
    res2 = await async_client.post(
        "/api/v1/auth/register",
        json={"full_name": "Alice", "email": "alice@example.com", "password": "short"},
    )
    assert res2.status_code == 422


@pytest.mark.asyncio
async def test_auth_me_unauthorized(async_client: AsyncClient):
    """Verifies that requesting /auth/me without a Bearer token returns 401."""
    res = await async_client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_refresh_token_invalid(async_client: AsyncClient):
    """Verifies that refreshing with a fake token returns 401."""
    res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "fake_invalid_token_1234567890"},
    )
    assert res.status_code == 401
