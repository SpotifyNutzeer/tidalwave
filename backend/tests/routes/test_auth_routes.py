from urllib.parse import parse_qs, urlsplit

from tidalwave.auth.session import COOKIE_NAME, SessionCodec


async def test_login_redirects_to_lastfm(api):
    client, app = api
    resp = await client.get("/auth/login", follow_redirects=False)
    assert resp.status_code == 307
    loc = resp.headers["location"]
    assert loc.startswith("https://www.last.fm/api/auth/")
    q = parse_qs(urlsplit(loc).query)
    assert q["api_key"] == ["KEY"]
    assert q["cb"] == ["http://test/auth/callback"]


async def test_callback_creates_user_and_sets_cookie(api):
    client, app = api
    from tidalwave.deps import get_lastfm_client

    class FakeLastfm:
        async def get_session(self, token):
            assert token == "TOK"
            return ("alice", "SESS")

    app.dependency_overrides[get_lastfm_client] = lambda: FakeLastfm()

    resp = await client.get("/auth/callback?token=TOK", follow_redirects=False)
    assert resp.status_code == 307
    cookie = resp.cookies[COOKIE_NAME]
    assert SessionCodec("test-secret").decode(cookie) is not None


async def test_me_returns_401_when_anonymous(api):
    client, app = api
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(api, db_session):
    from tidalwave.auth.service import upsert_user_from_session
    from tidalwave.auth.session import COOKIE_NAME, SessionCodec

    client, app = api
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    cookie = SessionCodec("test-secret").encode(user.id)
    resp = await client.get("/auth/me", headers={"Cookie": f"{COOKIE_NAME}={cookie}"})
    assert resp.status_code == 200
    assert resp.json() == {"username": "alice", "is_admin": True}


async def test_callback_schedules_immediate_ingest(api, monkeypatch):
    client, app = api
    from tidalwave.deps import get_lastfm_client
    from tidalwave.routes import auth as auth_module

    class FakeLastfm:
        async def get_session(self, token):
            return ("alice", "SESS")

    fake = FakeLastfm()
    app.dependency_overrides[get_lastfm_client] = lambda: fake

    calls = []

    async def spy(session_factory, lastfm_client, user_id):
        calls.append((session_factory, lastfm_client, user_id))

    monkeypatch.setattr(auth_module, "ingest_user_now", spy)

    resp = await client.get("/auth/callback?token=TOK", follow_redirects=False)
    assert resp.status_code == 307

    # FastAPI runs background tasks after the response is sent.
    assert len(calls) == 1
    session_factory, lastfm_client, user_id = calls[0]
    assert session_factory is app.state.session_factory
    assert lastfm_client is fake
    assert isinstance(user_id, int)
