from datetime import UTC, datetime

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.auth.session import COOKIE_NAME, SessionCodec
from tidalwave.ingest.repository import upsert_listens
from tidalwave.models.domain import Scrobble


async def test_stats_requires_auth(api):
    client, app = api
    resp = await client.get("/stats/top-artists")
    assert resp.status_code == 401


async def test_stats_returns_own_data(api, db_session):
    client, app = api
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    await upsert_listens(db_session, user.id, [
        Scrobble(artist="Daft Punk", track_title="a", album=None,
                 played_at=datetime.fromtimestamp(0, tz=UTC)),
    ])
    cookie = SessionCodec("test-secret").encode(user.id)
    resp = await client.get(
        "/stats/top-artists", headers={"Cookie": f"{COOKIE_NAME}={cookie}"}
    )
    assert resp.status_code == 200
    assert resp.json()[0] == {"artist": "Daft Punk", "count": 1}
