from datetime import UTC, datetime

from sqlalchemy import func, select

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.repository import (
    advance_sync_state,
    get_sync_state,
    upsert_listens,
)
from tidalwave.models.db import Listen
from tidalwave.models.domain import Scrobble


def _scrobble(title: str, ts: int) -> Scrobble:
    return Scrobble(
        artist="A", track_title=title, album="Alb",
        played_at=datetime.fromtimestamp(ts, tz=UTC),
    )


async def test_upsert_inserts_and_dedups(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    s = [_scrobble("t1", 1000), _scrobble("t2", 2000)]

    inserted = await upsert_listens(db_session, user.id, s)
    assert inserted == 2

    inserted2 = await upsert_listens(db_session, user.id, [*s, _scrobble("t3", 3000)])
    assert inserted2 == 1

    total = (
        await db_session.execute(select(func.count()).select_from(Listen))
    ).scalar_one()
    assert total == 3


async def test_now_playing_scrobbles_are_skipped(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    np = Scrobble(artist="A", track_title="np", album=None, played_at=None, now_playing=True)
    inserted = await upsert_listens(db_session, user.id, [np])
    assert inserted == 0


async def test_dateless_finished_scrobbles_are_skipped(db_session):
    # A finished track (now_playing=False) that lacks a timestamp cannot be stored.
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    dateless = Scrobble(artist="A", track_title="x", album=None, played_at=None, now_playing=False)
    inserted = await upsert_listens(db_session, user.id, [dateless])
    assert inserted == 0


async def test_sync_state_roundtrip(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    assert await get_sync_state(db_session, user.id) is None

    ts = datetime.fromtimestamp(5000, tz=UTC)
    await advance_sync_state(db_session, user.id, last_played_at=ts)
    state = await get_sync_state(db_session, user.id)
    assert state is not None and state.last_played_at == ts
