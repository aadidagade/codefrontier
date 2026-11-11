import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verifies that the root landing endpoint responds with service details."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["api_v1"] == "/api/v1"
    assert "x-request-id" in response.headers
    assert "x-process-time-ms" in response.headers


@pytest.mark.asyncio
async def test_overall_health(async_client: AsyncClient):
    """Verifies that /api/v1/health responds with service details."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "services" in data
    assert "database" in data["services"]
    assert "ai" in data["services"]


@pytest.mark.asyncio
async def test_database_health_endpoint(async_client: AsyncClient):
    """Verifies that /api/v1/health/database executes a real check."""
    response = await async_client.get("/api/v1/health/database")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "success" in data
    assert "data" in data
    assert "pgvector_enabled" in data["data"]


@pytest.mark.asyncio
async def test_ai_health_endpoint(async_client: AsyncClient):
    """Verifies that /api/v1/health/ai checks Gemini connectivity safely."""
    response = await async_client.get("/api/v1/health/ai")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "success" in data
    assert "data" in data
    # Ensure API key is NOT exposed in the response
    raw_text = response.text
    assert "AIzaSy" not in raw_text


@pytest.mark.asyncio
async def test_openapi_docs(async_client: AsyncClient):
    """Verifies OpenAPI JSON and Swagger schema generation."""
    response = await async_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Knowledge Handover Platform"
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/health/database" in schema["paths"]
    assert "/api/v1/health/ai" in schema["paths"]
    assert "/api/v1/auth/login" in schema["paths"]
    assert "/api/v1/handovers/generate" in schema["paths"]
