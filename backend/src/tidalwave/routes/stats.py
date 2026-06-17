from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.auth.session import current_user
from tidalwave.deps import get_session
from tidalwave.models.db import User
from tidalwave.stats import queries

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/top-artists")
async def top_artists(
    limit: int = 20,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    return await queries.top_artists(session, user.id, limit=limit)


@router.get("/top-tracks")
async def top_tracks(limit: int = 20, user: User = Depends(current_user),
                     session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await queries.top_tracks(session, user.id, limit=limit)


@router.get("/top-albums")
async def top_albums(limit: int = 20, user: User = Depends(current_user),
                     session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await queries.top_albums(session, user.id, limit=limit)


@router.get("/clock")
async def clock(user: User = Depends(current_user),
                session: AsyncSession = Depends(get_session)) -> list[int]:
    return await queries.listening_clock(session, user.id)


@router.get("/recent")
async def recent(limit: int = 50, user: User = Depends(current_user),
                 session: AsyncSession = Depends(get_session)) -> list[dict]:
    return await queries.recent_listens(session, user.id, limit=limit)


@router.get("/summary")
async def summary(user: User = Depends(current_user),
                  session: AsyncSession = Depends(get_session)) -> dict:
    return {"total_listens": await queries.total_listens(session, user.id)}
