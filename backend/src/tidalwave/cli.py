from __future__ import annotations

import argparse
import asyncio
import logging

import httpx
from sqlalchemy import select

from tidalwave.config import Settings
from tidalwave.db import make_engine, make_session_factory, session_scope
from tidalwave.ingest.poller import poll_all_users
from tidalwave.ingest.service import backfill_user
from tidalwave.lastfm.client import LastfmClient
from tidalwave.models.db import User


def _client(http: httpx.AsyncClient, settings: Settings) -> LastfmClient:
    return LastfmClient(http, api_key=settings.lastfm_api_key, api_secret=settings.lastfm_api_secret)


async def _poll() -> None:
    settings = Settings()
    logging.basicConfig(level=settings.log_level)
    factory = make_session_factory(make_engine(settings))
    async with httpx.AsyncClient(timeout=15.0) as http, session_scope(factory) as session:
        report = await poll_all_users(session, _client(http, settings))
        await session.commit()
        logging.getLogger("tidalwave").info("poll report: %s", report)


async def _backfill(username: str) -> None:
    settings = Settings()
    factory = make_session_factory(make_engine(settings))
    async with httpx.AsyncClient(timeout=15.0) as http, session_scope(factory) as session:
        user = (
            await session.execute(select(User).where(User.lastfm_username == username))
        ).scalar_one()
        inserted = await backfill_user(session, _client(http, settings), user)
        await session.commit()
        logging.getLogger("tidalwave").info("backfilled %s listens for %s", inserted, username)


def poll() -> None:
    asyncio.run(_poll())


def backfill() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    args = parser.parse_args()
    asyncio.run(_backfill(args.username))
