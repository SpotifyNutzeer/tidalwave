from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.ingest.service import RecentTracksSource, ingest_user
from tidalwave.lastfm.client import LastfmError
from tidalwave.models.db import User

log = logging.getLogger(__name__)


async def poll_all_users(
    session: AsyncSession, client: RecentTracksSource
) -> dict[str, int | str]:
    """Ingest for every connected user. Per-user failures are isolated, not raised."""
    users = (
        await session.execute(select(User).where(User.disconnected.is_(False)))
    ).scalars().all()
    report: dict[str, int | str] = {}
    for user in users:
        try:
            report[user.lastfm_username] = await ingest_user(session, client, user)
        except LastfmError:
            log.exception("ingest failed for %s", user.lastfm_username)
            report[user.lastfm_username] = "error"
    return report
