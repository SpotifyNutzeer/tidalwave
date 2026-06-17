from datetime import UTC, datetime

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.auth.session import COOKIE_NAME, SessionCodec
from tidalwave.ingest.repository import upsert_listens
from tidalwave.models.domain import Scrobble


def _auth_header(user_id: int) -> dict:
    cookie = SessionCodec("test-secret").encode(user_id)
    return {"Cookie": f"{COOKIE_NAME}={cookie}"}


async def test_share_create_then_public_view(api, db_session):
    client, app = api
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    await upsert_listens(db_session, user.id, [
        Scrobble(artist="Kavinsky", track_title="Nightcall", album=None,
                 played_at=datetime.fromtimestamp(0, tz=UTC)),
    ])

    created = await client.post("/shares", headers=_auth_header(user.id))
    assert created.status_code == 201
    token = created.json()["share_token"]

    view = await client.get(f"/shared/{token}/top-artists")  # public, no cookie
    assert view.status_code == 200
    assert view.json()[0] == {"artist": "Kavinsky", "count": 1}


async def test_revoked_share_returns_404(api, db_session):
    client, app = api
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    token = (await client.post("/shares", headers=_auth_header(user.id))).json()["share_token"]

    await client.delete(f"/shares/{token}", headers=_auth_header(user.id))
    view = await client.get(f"/shared/{token}/top-artists")
    assert view.status_code == 404


async def test_shared_full_dashboard_endpoints(api, db_session):
    from datetime import UTC, datetime
    from tidalwave.auth.service import upsert_user_from_session
    from tidalwave.auth.session import COOKIE_NAME, SessionCodec
    from tidalwave.ingest.repository import upsert_listens
    from tidalwave.models.domain import Scrobble

    client, app = api
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    await upsert_listens(db_session, user.id, [
        Scrobble(artist="Kavinsky", track_title="Nightcall", album="OutRun",
                 played_at=datetime(2024, 6, 17, 12, tzinfo=UTC)),
    ])
    cookie = SessionCodec("test-secret").encode(user.id)
    token = (await client.post("/shares", headers={"Cookie": f"{COOKIE_NAME}={cookie}"})).json()["share_token"]

    assert (await client.get(f"/shared/{token}/top-tracks")).json()[0]["track"] == "Nightcall"
    assert (await client.get(f"/shared/{token}/top-albums")).json()[0]["album"] == "OutRun"
    assert (await client.get(f"/shared/{token}/clock")).json()[12] == 1   # hour 12 UTC
    assert (await client.get(f"/shared/{token}/weekday")).json()[0] == 1  # Monday
    assert (await client.get(f"/shared/{token}/history?bucket=day")).json()[0]["count"] == 1
    assert (await client.get(f"/shared/{token}/recent")).json()[0]["track"] == "Nightcall"


async def test_shared_endpoints_404_when_revoked(api, db_session):
    from tidalwave.auth.service import upsert_user_from_session
    from tidalwave.auth.session import COOKIE_NAME, SessionCodec

    client, app = api
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    auth = {"Cookie": f"{COOKIE_NAME}={SessionCodec('test-secret').encode(user.id)}"}
    token = (await client.post("/shares", headers=auth)).json()["share_token"]
    await client.delete(f"/shares/{token}", headers=auth)
    assert (await client.get(f"/shared/{token}/top-tracks")).status_code == 404
    assert (await client.get(f"/shared/{token}/clock")).status_code == 404
