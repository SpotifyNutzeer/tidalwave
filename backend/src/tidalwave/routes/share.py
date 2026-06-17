from __future__ import annotations

import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.auth.session import current_user
from tidalwave.deps import get_session
from tidalwave.models.db import Share, User
from tidalwave.stats import queries

router = APIRouter(tags=["share"])


@router.post("/shares", status_code=201)
async def create_share(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    token = secrets.token_urlsafe(32)
    session.add(Share(share_token=token, user_id=user.id))
    await session.flush()
    return {"share_token": token}


@router.delete("/shares/{token}", status_code=204)
async def revoke_share(
    token: str,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    await session.execute(
        update(Share)
        .where(Share.share_token == token, Share.user_id == user.id, Share.revoked_at.is_(None))
        .values(revoked_at=func.now())
    )


async def _resolve_share(session: AsyncSession, token: str) -> Share:
    share = (
        await session.execute(
            select(Share).where(Share.share_token == token, Share.revoked_at.is_(None))
        )
    ).scalar_one_or_none()
    if share is None:
        raise HTTPException(status_code=404, detail="Share not found")
    return share


@router.get("/shared/{token}/top-artists")
async def shared_top_artists(
    token: str, limit: int = 20, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    share = await _resolve_share(session, token)
    return await queries.top_artists(
        session, share.user_id, limit=limit, since=share.range_from, until=share.range_to
    )


@router.get("/shared/{token}/summary")
async def shared_summary(
    token: str, session: AsyncSession = Depends(get_session)
) -> dict:
    share = await _resolve_share(session, token)
    total = await queries.total_listens(
        session, share.user_id, since=share.range_from, until=share.range_to
    )
    return {"total_listens": total}


@router.get("/shared/{token}/top-tracks")
async def shared_top_tracks(
    token: str, limit: int = 20, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    share = await _resolve_share(session, token)
    return await queries.top_tracks(
        session, share.user_id, limit=limit, since=share.range_from, until=share.range_to
    )


@router.get("/shared/{token}/top-albums")
async def shared_top_albums(
    token: str, limit: int = 20, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    share = await _resolve_share(session, token)
    return await queries.top_albums(
        session, share.user_id, limit=limit, since=share.range_from, until=share.range_to
    )


@router.get("/shared/{token}/clock")
async def shared_clock(
    token: str, session: AsyncSession = Depends(get_session)
) -> list[int]:
    share = await _resolve_share(session, token)
    return await queries.listening_clock(
        session, share.user_id, since=share.range_from, until=share.range_to
    )


@router.get("/shared/{token}/weekday")
async def shared_weekday(
    token: str, session: AsyncSession = Depends(get_session)
) -> list[int]:
    share = await _resolve_share(session, token)
    return await queries.listening_weekday(
        session, share.user_id, since=share.range_from, until=share.range_to
    )


@router.get("/shared/{token}/history")
async def shared_history(
    token: str,
    bucket: Literal["day", "week", "month"] = "day",
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    share = await _resolve_share(session, token)
    return await queries.listens_over_time(
        session, share.user_id, bucket=bucket, since=share.range_from, until=share.range_to
    )


@router.get("/shared/{token}/recent")
async def shared_recent(
    token: str, limit: int = 50, session: AsyncSession = Depends(get_session)
) -> list[dict]:
    share = await _resolve_share(session, token)
    return await queries.recent_listens(session, share.user_id, limit=limit)
