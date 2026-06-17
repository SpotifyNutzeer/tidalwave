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
