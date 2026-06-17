import httpx
import pytest
import respx

from tidalwave.lastfm.client import LastfmClient, LastfmError


@pytest.fixture
async def client():
    async with httpx.AsyncClient() as http:
        yield LastfmClient(http, api_key="KEY", api_secret="SECRET")


@respx.mock
async def test_get_session_returns_username_and_key(client):
    respx.get("https://ws.audioscrobbler.com/2.0/").respond(
        json={"session": {"name": "alice", "key": "SESS123", "subscriber": 0}}
    )
    result = await client.get_session("TOKEN")
    assert result == ("alice", "SESS123")


@respx.mock
async def test_get_session_raises_on_lastfm_error(client):
    respx.get("https://ws.audioscrobbler.com/2.0/").respond(
        json={"error": 14, "message": "Unauthorized Token"}
    )
    with pytest.raises(LastfmError):
        await client.get_session("BADTOKEN")
