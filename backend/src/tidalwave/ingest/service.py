from __future__ import annotations

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.ingest.repository import advance_sync_state, get_sync_state, upsert_listens
from tidalwave.lastfm.client import RecentTracksPage
from tidalwave.models.db import User
from tidalwave.models.domain import Scrobble


class RecentTracksSource(Protocol):
    async def get_recent_tracks(
        self, username: str, *, from_ts: int | None = ..., page: int = ..., limit: int = ...
    ) -> RecentTracksPage: ...


async def ingest_user(
    session: AsyncSession, client: RecentTracksSource, user: User
) -> int:
    """Fetch all scrobbles since the last sync and store them. Returns inserted count."""
    state = await get_sync_state(session, user.id)
    from_ts: int | None = None
    if state is not None and state.last_played_at is not None:
        # Last.fm `from` is inclusive; +1s avoids re-fetching the boundary scrobble.
        from_ts = int(state.last_played_at.timestamp()) + 1

    collected: list[Scrobble] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        result = await client.get_recent_tracks(user.lastfm_username, from_ts=from_ts, page=page)
        total_pages = result.total_pages
        collected.extend(result.scrobbles)
        page += 1

    inserted = await upsert_listens(session, user.id, collected)

    newest = max((s.played_at for s in collected if s.played_at is not None), default=None)
    if newest is not None:
        await advance_sync_state(session, user.id, last_played_at=newest)
    return inserted
