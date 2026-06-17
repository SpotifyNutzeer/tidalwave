from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.models.db import Listen, SyncState
from tidalwave.models.domain import Scrobble


async def upsert_listens(
    session: AsyncSession, user_id: int, scrobbles: list[Scrobble]
) -> int:
    """Insert datable scrobbles, skipping any without a timestamp and any duplicates.

    Returns the number of rows actually inserted. Scrobbles with ``played_at is None``
    (now-playing tracks and dateless tracks) are skipped — they cannot be stored because
    ``played_at`` is part of the dedup key and is NOT NULL.
    """
    rows = [
        {
            "user_id": user_id,
            "track_title": s.track_title,
            "artist": s.artist,
            "album": s.album,
            "played_at": s.played_at,
            "track_mbid": s.track_mbid,
            "artist_mbid": s.artist_mbid,
            "album_mbid": s.album_mbid,
        }
        for s in scrobbles
        if s.played_at is not None
    ]
    if not rows:
        return 0
    stmt = (
        pg_insert(Listen)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_listen_dedup")
        .returning(Listen.id)
    )
    result = await session.execute(stmt)
    return len(result.fetchall())


async def get_sync_state(session: AsyncSession, user_id: int) -> SyncState | None:
    return (
        await session.execute(select(SyncState).where(SyncState.user_id == user_id))
    ).scalar_one_or_none()


async def advance_sync_state(
    session: AsyncSession, user_id: int, *, last_played_at: datetime
) -> None:
    stmt = (
        pg_insert(SyncState)
        .values(user_id=user_id, last_played_at=last_played_at, last_synced_at=func.now())
        .on_conflict_do_update(
            index_elements=[SyncState.user_id],
            set_={"last_played_at": last_played_at, "last_synced_at": func.now()},
        )
    )
    await session.execute(stmt)
