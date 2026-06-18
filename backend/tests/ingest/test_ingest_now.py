from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.poller import ingest_user_now
from tidalwave.lastfm.client import LastfmError, RecentTracksPage
from tidalwave.models.db import Listen
from tidalwave.models.domain import Scrobble


class FakeClient:
    def __init__(self, by_user, errors=None):
        self.by_user = by_user
        self.errors: dict[str, LastfmError] = errors or {}

    async def get_recent_tracks(self, username, *, from_ts=None, page=1, limit=200, session_key=None):
        if username in self.errors:
            raise self.errors[username]
        return self.by_user[username]


def _page(ts):
    return RecentTracksPage(
        (Scrobble(artist="A", track_title="t", album=None,
                  played_at=datetime.fromtimestamp(ts, tz=UTC)),),
        page=1, total_pages=1,
    )


@pytest_asyncio.fixture
async def committing_factory(_engine):
    # A factory whose sessions share one connection via SAVEPOINTs, so the
    # real commit() inside ingest_user_now is visible to later reads in the
    # test yet fully rolled back at teardown.
    connection = await _engine.connect()
    trans = await connection.begin()
    factory = async_sessionmaker(
        bind=connection, expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield factory
    finally:
        await trans.rollback()
        await connection.close()


async def test_ingest_user_now_stores_listens(committing_factory):
    async with committing_factory() as s:
        user = await upsert_user_from_session(s, "alice", "sk", mode="open", allowlist=[])
        await s.commit()
        uid = user.id

    await ingest_user_now(committing_factory, FakeClient({"alice": _page(1000)}), uid)

    async with committing_factory() as s:
        listens = (await s.execute(select(Listen).where(Listen.user_id == uid))).scalars().all()
    assert len(listens) == 1


async def test_ingest_user_now_noops_for_missing_user(committing_factory):
    # Must not raise when the user id does not exist.
    await ingest_user_now(committing_factory, FakeClient({}), 999999)


async def test_ingest_user_now_swallows_unexpected_error(committing_factory):
    class BoomClient:
        async def get_recent_tracks(self, username, *, from_ts=None, page=1, limit=200, session_key=None):
            raise ValueError("boom")

    async with committing_factory() as s:
        user = await upsert_user_from_session(s, "bob", "sk", mode="open", allowlist=[])
        await s.commit()
        uid = user.id

    # Must not raise — the contract is fire-and-forget after the HTTP response.
    await ingest_user_now(committing_factory, BoomClient(), uid)


async def test_ingest_user_now_is_incremental_on_repeat(committing_factory):
    async with committing_factory() as s:
        user = await upsert_user_from_session(s, "carol", "sk", mode="open", allowlist=[])
        await s.commit()
        uid = user.id

    await ingest_user_now(committing_factory, FakeClient({"carol": _page(1000)}), uid)
    await ingest_user_now(committing_factory, FakeClient({"carol": _page(2000)}), uid)

    async with committing_factory() as s:
        listens = (await s.execute(select(Listen).where(Listen.user_id == uid))).scalars().all()
    assert len(listens) == 2
