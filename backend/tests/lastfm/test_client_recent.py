import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from tidalwave.lastfm.client import LastfmClient

FIX = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def client():
    async with httpx.AsyncClient() as http:
        yield LastfmClient(http, api_key="KEY", api_secret="SECRET")


@respx.mock
async def test_parses_recent_tracks_and_nowplaying(client):
    payload = json.loads((FIX / "recent_tracks_page1.json").read_text())
    respx.get("https://ws.audioscrobbler.com/2.0/").respond(json=payload)

    page = await client.get_recent_tracks("alice", page=1)

    assert page.page == 1
    assert page.total_pages == 2
    assert len(page.scrobbles) == 2

    np = page.scrobbles[0]
    assert np.now_playing is True
    assert np.played_at is None
    assert np.track_title == "Nightcall"

    done = page.scrobbles[1]
    assert done.now_playing is False
    assert done.played_at == datetime.fromtimestamp(1700000000, tz=UTC)
    assert done.artist == "Daft Punk"
    assert done.album == "Discovery"
    assert done.album_mbid is None  # empty string normalized to None
