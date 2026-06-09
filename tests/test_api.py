"""
Minimal integration tests for the FastAPI app using an in‑memory SQLite DB.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Override the database URL before importing main
from app.core.config import settings
settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"

from app.main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_predictions_empty(client):
    response = await client.get("/api/v1/predict")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_metrics_initial(client):
    response = await client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "current_occupancy" in data
    assert "alerts" in data


@pytest.mark.asyncio
async def test_trigger_simulation(client):
    response = await client.post("/api/v1/simulation/trigger?scenario=standard")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert len(data["volumes"]) == 2


@pytest.mark.asyncio
async def test_trigger_invalid_scenario(client):
    response = await client.post("/api/v1/simulation/trigger?scenario=invalid")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_dashboard(client):
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "interval_start" in data[0]
        assert "real_call_volume" in data[0] or data[0]["real_call_volume"] is None

@pytest.mark.asyncio
async def test_get_dashboard(client):
    # Ensure at least one forecast and one historical point exist
    # (scheduler may have already injected)
    response = await client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # If empty it's acceptable (no data yet), but structure must be correct
    if data:
        assert "interval_start" in data[0]
        assert "real_call_volume" in data[0] or data[0]["real_call_volume"] is None