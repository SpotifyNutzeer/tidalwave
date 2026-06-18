from __future__ import annotations

import asyncio
import logging
from typing import Any, Protocol, cast

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.lastfm.client import LastfmError
from tidalwave.models.db import Listen, TrackDuration

log = logging.getLogger(__name__)


class TrackInfoSource(Protocol):
    async def get_track_info(self, artist: str, track: str) -> int | None: ...


async def fill_missing_durations(
    session: AsyncSession,
    client: TrackInfoSource,
    *,
    user_id: int | None = None,
    max_tracks: int | None = None,
) -> int:
    """Resolve track lengths for listens that don't have one yet.

    Finds distinct (artist, track) pairs among listens with ``duration_sec IS
    NULL``, looks each up in the ``track_durations`` cache, fetches from Last.fm
    on a miss, then writes the length back onto the matching listens.

    ``max_tracks`` caps how many distinct tracks are processed per call (keeps
    the 5-minute poll bounded); ``user_id`` scopes the work to one user. Returns
    the number of listen rows updated.
    """
    stmt = select(Listen.artist, Listen.track_title).where(Listen.duration_sec.is_(None))
    if user_id is not None:
        stmt = stmt.where(Listen.user_id == user_id)
    stmt = stmt.distinct()
    if max_tracks is not None:
        stmt = stmt.limit(max_tracks)

    pairs = [(row[0], row[1]) for row in (await session.execute(stmt)).all()]
    if not pairs:
        return 0

    updated = 0
    for artist, track in pairs:
        duration = await _resolve_one(session, client, artist, track)
        if duration is None:
            continue
        upd = update(Listen).where(
            Listen.artist == artist,
            Listen.track_title == track,
            Listen.duration_sec.is_(None),
        )
        if user_id is not None:
            upd = upd.where(Listen.user_id == user_id)
        result = cast("CursorResult[Any]", await session.execute(upd.values(duration_sec=duration)))
        updated += result.rowcount or 0
    return updated


async def _resolve_one(
    session: AsyncSession, client: TrackInfoSource, artist: str, track: str
) -> int | None:
    """Return a track's length in seconds via the cache, fetching once on a miss."""
    cached = (
        await session.execute(
            select(TrackDuration.duration_sec).where(
                TrackDuration.artist == artist, TrackDuration.track_title == track
            )
        )
    ).first()
    if cached is not None:
        return cached[0]

    duration: int | None = None
    try:
        duration = await client.get_track_info(artist, track)
        await asyncio.sleep(0.1)  # be polite to the Last.fm API on cache misses
    except LastfmError as e:
        log.warning("track.getInfo failed for %s — %s: %s", artist, track, e)
    except Exception:
        log.exception("track.getInfo errored for %s — %s", artist, track)

    # Cache the outcome (even None) so we don't keep re-requesting the same track.
    await session.execute(
        pg_insert(TrackDuration)
        .values(artist=artist, track_title=track, duration_sec=duration)
        .on_conflict_do_nothing(constraint="uq_track_duration")
    )
    return duration
