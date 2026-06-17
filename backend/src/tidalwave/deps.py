from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.config import Settings
from tidalwave.lastfm.client import LastfmClient


@lru_cache
def get_settings() -> Settings:
    return Settings()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session
        await session.commit()


def get_lastfm_client(
    request: Request, settings: Settings = Depends(get_settings)
) -> LastfmClient:
    return LastfmClient(
        request.app.state.http,
        api_key=settings.lastfm_api_key,
        api_secret=settings.lastfm_api_secret,
    )
