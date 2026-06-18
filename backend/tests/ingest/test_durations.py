from datetime import UTC, datetime

from sqlalchemy import select

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.durations import fill_missing_durations
from tidalwave.ingest.repository import upsert_listens
from tidalwave.models.db import Listen, TrackDuration
from tidalwave.models.domain import Scrobble


class FakeInfoClient:
    """Returns durations (in seconds) per (artist, track); counts lookups."""

    def __init__(self, durations):
        self.durations = durations
        self.calls = 0

    async def get_track_info(self, artist, track):
        self.calls += 1
        return self.durations.get((artist, track))


def _sc(artist, title, ts):
    return Scrobble(artist=artist, track_title=title, album=None,
                    played_at=datetime.fromtimestamp(ts, tz=UTC))


async def test_fills_durations_and_caches(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    await upsert_listens(db_session, user.id, [
        _sc("A", "song", 0),
        _sc("A", "song", 86400),   # same track, played twice → both get the duration
        _sc("B", "other", 172800),  # Last.fm has no duration → stays NULL
    ])

    client = FakeInfoClient({("A", "song"): 215})
    updated = await fill_missing_durations(db_session, client, user_id=user.id)

    assert updated == 2  # both "A — song" rows
    durations = (
        await db_session.execute(select(Listen.duration_sec).order_by(Listen.played_at))
    ).scalars().all()
    assert durations == [215, 215, None]

    # Every unique (artist, track) is cached — including the unknown one (None).
    cached = (await db_session.execute(select(TrackDuration))).scalars().all()
    assert {(c.artist, c.track_title): c.duration_sec for c in cached} == {
        ("A", "song"): 215,
        ("B", "other"): None,
    }


async def test_cache_prevents_refetch(db_session):
    user = await upsert_user_from_session(db_session, "bob", "sk", mode="open", allowlist=[])
    await upsert_listens(db_session, user.id, [_sc("A", "song", 0)])

    client = FakeInfoClient({("A", "song"): 200})
    await fill_missing_durations(db_session, client, user_id=user.id)
    assert client.calls == 1

    # A new listen of the same track must reuse the cache, not call the API again.
    await upsert_listens(db_session, user.id, [_sc("A", "song", 86400)])
    await fill_missing_durations(db_session, client, user_id=user.id)
    assert client.calls == 1  # no extra lookup
