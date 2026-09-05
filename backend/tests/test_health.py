"""
Tests for the /health and / endpoints.

Uses httpx.AsyncClient with ASGITransport (no live server needed).
pytest-anyio drives the async test functions.
"""

import pytest
import httpx
from httpx import ASGITransport

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_health_status_code(client) -> None:
    """GET /health must return HTTP 200."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_health_response_body(client) -> None:
    """GET /health must return the exact expected JSON payload."""
    response = await client.get("/health")
    assert response.json() == {
        "status": "ok",
        "service": "revenue-recovery-agent",
    }


@pytest.mark.anyio
async def test_health_content_type(client) -> None:
    """GET /health must respond with application/json."""
    response = await client.get("/health")
    assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# /
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_root_status_code(client) -> None:
    """GET / must return HTTP 200."""
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_root_response_body(client) -> None:
    """GET / must return a JSON object that identifies the API."""
    response = await client.get("/")
    body = response.json()
    assert body["api"] == "Revenue Recovery Agent"
    assert "version" in body
    assert "docs" in body
