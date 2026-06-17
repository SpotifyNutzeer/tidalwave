from datetime import UTC, datetime

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.poller import poll_all_users
from tidalwave.lastfm.client import LastfmError, RecentTracksPage
from tidalwave.models.domain import Scrobble


class FakeClient:
    def __init__(self, by_user):
        self.by_user = by_user

    async def get_recent_tracks(self, username, *, from_ts=None, page=1, limit=200):
        if username == "boom":
            raise LastfmError(8, "operation failed")
        return self.by_user[username]


def _page(ts):
    return RecentTracksPage(
        (Scrobble(artist="A", track_title="t", album=None,
                  played_at=datetime.fromtimestamp(ts, tz=UTC)),),
        page=1, total_pages=1,
    )


async def test_poll_processes_every_connected_user_and_isolates_failures(db_session):
    await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    boom = await upsert_user_from_session(db_session, "boom", "sk", mode="open", allowlist=[])
    boom.disconnected = False
    skipped = await upsert_user_from_session(db_session, "carol", "sk", mode="open", allowlist=[])
    skipped.disconnected = True
    await db_session.flush()

    client = FakeClient({"alice": _page(1000), "carol": _page(1000)})
    report = await poll_all_users(db_session, client)

    assert report["alice"] == 1
    assert report["boom"] == "error"   # failure isolated, not raised
    assert "carol" not in report        # disconnected users skipped
