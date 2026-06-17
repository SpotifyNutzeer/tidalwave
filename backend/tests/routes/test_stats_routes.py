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


async def test_summary_since_filters_listens(api, db_session):
    client, app = api
    user = await upsert_user_from_session(db_session, "bob", "sk2", mode="open", allowlist=[])
    await upsert_listens(db_session, user.id, [
        Scrobble(artist="Artist A", track_title="old", album=None,
                 played_at=datetime(2024, 1, 1, tzinfo=UTC)),
        Scrobble(artist="Artist A", track_title="new1", album=None,
                 played_at=datetime(2024, 6, 1, tzinfo=UTC)),
        Scrobble(artist="Artist B", track_title="new2", album=None,
                 played_at=datetime(2024, 7, 1, tzinfo=UTC)),
    ])
    cookie = SessionCodec("test-secret").encode(user.id)
    # only listens at or after 2024-06-01 should be counted (2 of 3)
    resp = await client.get(
        "/stats/summary?since=2024-06-01T00:00:00",
        headers={"Cookie": f"{COOKIE_NAME}={cookie}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"total_listens": 2}
