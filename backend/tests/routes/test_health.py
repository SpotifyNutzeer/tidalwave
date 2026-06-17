import httpx
import pytest

from tidalwave.main import create_app


@pytest.fixture
async def app_client(monkeypatch):
    monkeypatch.setenv(
        "TIDALWAVE_DATABASE_URL",
        "postgresql+asyncpg://tidalwave:tidalwave@localhost:5432/tidalwave",
    )
    from tidalwave.deps import get_settings
    get_settings.cache_clear()
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    get_settings.cache_clear()


async def test_health_ok(app_client):
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
