from datetime import UTC, datetime

from sqlalchemy import func, select

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.service import backfill_user
from tidalwave.lastfm.client import RecentTracksPage
from tidalwave.models.db import Listen
from tidalwave.models.domain import Scrobble


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def get_recent_tracks(self, username, *, from_ts=None, page=1, limit=200, session_key=None):
        self.calls.append((from_ts, page))
        return self.pages[page]


def _sc(title, ts):
    return Scrobble(artist="A", track_title=title, album=None,
                    played_at=datetime.fromtimestamp(ts, tz=UTC))


async def test_backfill_ignores_sync_floor_and_is_idempotent(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    pages = {1: RecentTracksPage((_sc("t1", 1000),), page=1, total_pages=1)}

    first = await backfill_user(db_session, FakeClient(pages), user)
    assert first == 1

    again = await backfill_user(db_session, FakeClient(pages), user)
    assert again == 0  # idempotent

    total = (await db_session.execute(select(func.count()).select_from(Listen))).scalar_one()
    assert total == 1


async def test_backfill_never_sends_a_from_floor(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    pages = {1: RecentTracksPage((_sc("t1", 1000),), page=1, total_pages=1)}
    client = FakeClient(pages)
    await backfill_user(db_session, client, user)
    # backfill must request page 1 with from_ts=None
    assert client.calls[0] == (None, 1)
