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
