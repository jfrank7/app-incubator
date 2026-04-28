import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    async with LifespanManager(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_run(client: AsyncClient):
    payload = {
        "raw_idea": "track caffeine intake daily",
        "form_answers": {
            "app_goal": "help users reduce caffeine",
            "target_user": "health-conscious adults",
            "top_3_actions": ["log drink", "view daily total", "set reduction goal"],
            "must_have_screens": ["dashboard", "add entry", "history"],
            "works_offline": True,
            "needs_notifications": False,
            "core_data_entities": ["CaffeineEntry", "DailyGoal"],
            "style_notes": "clean minimal",
            "constraints_non_goals": "no social features",
        },
    }
    r = await client.post("/api/runs", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient):
    r = await client.get("/api/runs")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_get_run_not_found(client: AsyncClient):
    r = await client.get("/api/runs/nonexistent-id")
    assert r.status_code == 404
