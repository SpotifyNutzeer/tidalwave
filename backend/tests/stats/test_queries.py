from datetime import UTC, datetime

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.repository import upsert_listens
from tidalwave.models.domain import Scrobble
from tidalwave.stats.queries import (
    listening_clock,
    top_artists,
    total_listens,
)


def _sc(artist, title, ts):
    return Scrobble(artist=artist, track_title=title, album=None,
                    played_at=datetime.fromtimestamp(ts, tz=UTC))


async def _seed(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    # 2 Daft Punk, 1 Kavinsky; timestamps at hour 0 UTC (ts multiples of 86400)
    await upsert_listens(db_session, user.id, [
        _sc("Daft Punk", "a", 0),
        _sc("Daft Punk", "b", 86400),
        _sc("Kavinsky", "c", 172800),
    ])
    return user


async def test_top_artists_ranks_by_count(db_session):
    user = await _seed(db_session)
    rows = await top_artists(db_session, user.id, limit=10)
    assert rows[0] == {"artist": "Daft Punk", "count": 2}
    assert rows[1] == {"artist": "Kavinsky", "count": 1}


async def test_total_listens(db_session):
    user = await _seed(db_session)
    assert await total_listens(db_session, user.id) == 3


async def test_listening_clock_buckets_by_hour(db_session):
    user = await _seed(db_session)
    clock = await listening_clock(db_session, user.id)
    assert clock[0] == 3  # all three at UTC hour 0
    assert len(clock) == 24


async def test_top_artists_isolated_per_user(db_session):
    await _seed(db_session)
    bob = await upsert_user_from_session(db_session, "bob", "sk", mode="open", allowlist=[])
    assert await top_artists(db_session, bob.id, limit=10) == []
