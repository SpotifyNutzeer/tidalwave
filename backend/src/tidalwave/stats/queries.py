from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, cast, distinct, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.models.db import Listen


def _scope(stmt, user_id: int, since: datetime | None, until: datetime | None):
    stmt = stmt.where(Listen.user_id == user_id)
    if since is not None:
        stmt = stmt.where(Listen.played_at >= since)
    if until is not None:
        stmt = stmt.where(Listen.played_at < until)
    return stmt


async def _top(session, user_id, column, label, *, limit, since, until):
    stmt = _scope(
        select(column.label(label), func.count().label("count")), user_id, since, until
    ).group_by(column).order_by(func.count().desc(), column.asc()).limit(limit)
    return [
        {label: row[0], "count": row[1]} for row in (await session.execute(stmt)).all()
    ]


async def top_artists(session: AsyncSession, user_id: int, *, limit: int = 20,
                      since=None, until=None) -> list[dict]:
    return await _top(session, user_id, Listen.artist, "artist",
                      limit=limit, since=since, until=until)


async def top_tracks(session: AsyncSession, user_id: int, *, limit: int = 20,
                     since=None, until=None) -> list[dict]:
    return await _top(session, user_id, Listen.track_title, "track",
                      limit=limit, since=since, until=until)


async def top_albums(session: AsyncSession, user_id: int, *, limit: int = 20,
                     since=None, until=None) -> list[dict]:
    return await _top(session, user_id, Listen.album, "album",
                      limit=limit, since=since, until=until)


async def total_listens(session: AsyncSession, user_id: int, *, since=None, until=None) -> int:
    stmt = _scope(select(func.count()).select_from(Listen), user_id, since, until)
    return (await session.execute(stmt)).scalar_one()


async def summary_stats(session: AsyncSession, user_id: int, *, since=None, until=None) -> dict:
    """Headline totals for the overview: listens, distinct artists/tracks/albums
    and total seconds listened (summed from resolved track durations)."""
    stmt = _scope(
        select(
            func.count().label("total_listens"),
            func.count(distinct(Listen.artist)).label("distinct_artists"),
            func.count(distinct(tuple_(Listen.artist, Listen.track_title))).label("distinct_tracks"),
            func.count(distinct(Listen.album)).label("distinct_albums"),
            func.coalesce(func.sum(Listen.duration_sec), 0).label("total_seconds"),
        ),
        user_id, since, until,
    )
    row = (await session.execute(stmt)).one()
    return {
        "total_listens": int(row.total_listens),
        "distinct_artists": int(row.distinct_artists),
        "distinct_tracks": int(row.distinct_tracks),
        "distinct_albums": int(row.distinct_albums),
        "total_seconds": int(row.total_seconds),
    }


async def metrics_over_time(session: AsyncSession, user_id: int, *, bucket: str = "day",
                            since=None, until=None) -> list[dict]:
    """Per-period listens, distinct artists/albums and seconds — drives the
    over-time graphs. Returns chronological rows keyed by ISO period."""
    period = func.date_trunc(bucket, func.timezone("UTC", Listen.played_at))
    stmt = (
        _scope(
            select(
                period.label("period"),
                func.count().label("listens"),
                func.count(distinct(Listen.artist)).label("artists"),
                func.count(distinct(Listen.album)).label("albums"),
                func.coalesce(func.sum(Listen.duration_sec), 0).label("seconds"),
            ),
            user_id, since, until,
        )
        .group_by(period)
        .order_by(period.asc())
    )
    return [
        {
            "period": row.period.isoformat(),
            "listens": int(row.listens),
            "artists": int(row.artists),
            "albums": int(row.albums),
            "seconds": int(row.seconds),
        }
        for row in (await session.execute(stmt)).all()
    ]


async def listening_clock(session: AsyncSession, user_id: int, *,
                          since=None, until=None) -> list[int]:
    """Returns a 24-element list: listens per UTC hour-of-day."""
    hour = cast(func.extract("hour", func.timezone("UTC", Listen.played_at)), Integer)
    stmt = _scope(select(hour, func.count()), user_id, since, until).group_by(hour)
    counts = {int(h): int(c) for h, c in (await session.execute(stmt)).all()}
    return [counts.get(h, 0) for h in range(24)]


async def listening_weekday(session: AsyncSession, user_id: int, *,
                            since=None, until=None) -> list[int]:
    """Returns a 7-element list: listens per ISO weekday, index 0 = Monday .. 6 = Sunday."""
    dow = cast(func.extract("isodow", func.timezone("UTC", Listen.played_at)), Integer)
    stmt = _scope(select(dow, func.count()), user_id, since, until).group_by(dow)
    counts = {int(d): int(c) for d, c in (await session.execute(stmt)).all()}
    return [counts.get(d, 0) for d in range(1, 8)]


async def listens_over_time(session: AsyncSession, user_id: int, *, bucket: str = "day",
                            since=None, until=None) -> list[dict]:
    """Listens grouped by calendar period. `bucket` is one of day|week|month.

    Returns chronological [{"period": <iso date/datetime>, "count": <int>}].
    """
    period = func.date_trunc(bucket, func.timezone("UTC", Listen.played_at))
    stmt = (
        _scope(select(period.label("period"), func.count().label("count")), user_id, since, until)
        .group_by(period)
        .order_by(period.asc())
    )
    return [
        {"period": row[0].isoformat(), "count": row[1]}
        for row in (await session.execute(stmt)).all()
    ]


async def recent_listens(session: AsyncSession, user_id: int, *, limit: int = 50,
                         since=None, until=None) -> list[dict]:
    stmt = _scope(
        select(Listen.track_title, Listen.artist, Listen.album, Listen.played_at),
        user_id, since, until,
    ).order_by(Listen.played_at.desc()).limit(limit)
    return [
        {"track": r[0], "artist": r[1], "album": r[2], "played_at": r[3].isoformat()}
        for r in (await session.execute(stmt)).all()
    ]
