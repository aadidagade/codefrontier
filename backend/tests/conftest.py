import os
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def async_client():
    """Provides an asynchronous test client mounted on the FastAPI application."""
    from app.dependencies.database import get_db
    from unittest.mock import AsyncMock, MagicMock

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = None
    mock_res.scalars.return_value.all.return_value = []
    mock_res.rowcount = 1
    mock_db.execute.return_value = mock_res

    async def override_get_db():
        yield mock_db

    orig_override = app.dependency_overrides.get(get_db)
    if get_db not in app.dependency_overrides:
        app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        if orig_override is not None:
            app.dependency_overrides[get_db] = orig_override
        else:
            app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Resets the in-memory rate limiter before each test to prevent cross-test 429 throttling."""
    from app.core.rate_limit import _limiter
    with _limiter._lock:
        _limiter._requests.clear()
    yield
    with _limiter._lock:
        _limiter._requests.clear()

