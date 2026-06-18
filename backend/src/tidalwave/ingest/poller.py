from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.ingest.service import RecentTracksSource, ingest_user
from tidalwave.lastfm.client import LastfmError
from tidalwave.models.db import User

log = logging.getLogger(__name__)

# Last.fm error codes that mean the session key is invalid / revoked.
# The user must reconnect; keep polling them forever serves no purpose.
_AUTH_ERROR_CODES = {4, 9}


async def ingest_one_user(
    session: AsyncSession, client: RecentTracksSource, user: User
) -> int | str:
    """Ingest one user. Returns inserted count, or "disconnected"/"error".

    Auth errors (codes 4/9) flip user.disconnected; transient errors are logged.
    Does not commit — the caller owns the transaction.
    """
    try:
        return await ingest_user(session, client, user)
    except LastfmError as e:
        log.exception("ingest failed for %s", user.lastfm_username)
        if e.code in _AUTH_ERROR_CODES:
            user.disconnected = True
            await session.flush()
            return "disconnected"
        return "error"


async def poll_all_users(
    session: AsyncSession, client: RecentTracksSource
) -> dict[str, int | str]:
    """Ingest for every connected user. Per-user failures are isolated, not raised."""
    users = (
        await session.execute(select(User).where(User.disconnected.is_(False)))
    ).scalars().all()
    report: dict[str, int | str] = {}
    for user in users:
        report[user.lastfm_username] = await ingest_one_user(session, client, user)
    return report
