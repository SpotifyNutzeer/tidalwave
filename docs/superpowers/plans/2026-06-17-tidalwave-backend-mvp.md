# tidalwave Backend MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the testable backend for `tidalwave` — a multi-user Tidal listening tracker that ingests scrobbles from Last.fm and exposes stats via a FastAPI API.

**Architecture:** FastAPI + SQLAlchemy 2 (async) + Postgres. Data comes from Last.fm (`user.getRecentTracks`); users connect via Last.fm's OAuth-like web-auth flow (connect = account creation + login). A poller ingests new scrobbles per user into a deduplicated `listens` time-series; stats endpoints aggregate it, gated per-user, with shareable read-only links.

**Tech Stack:** Python 3.12 (uv), FastAPI, SQLAlchemy 2 async, asyncpg, Alembic, httpx, pydantic-settings, pytest (+ pytest-asyncio, respx). Conventions mirror the sibling `linkhop` project.

**Scope:** Backend only. Frontend (SvelteKit dashboards) and Helm/Flux deployment are a separate follow-up plan.

---

## File Structure

```
tidalwave/
  backend/
    pyproject.toml                  # uv project, deps, ruff/mypy/pytest config
    .python-version                 # 3.12
    docker-compose.yml              # Postgres for local dev + tests
    alembic.ini
    migrations/                     # Alembic env + versions
    src/tidalwave/
      __init__.py
      config.py                     # Settings (TIDALWAVE_ env prefix)
      db.py                         # engine/session helpers
      models/
        __init__.py
        db.py                       # SQLAlchemy ORM models: User, Listen, SyncState, Share
        domain.py                   # dataclasses: Scrobble (parsed Last.fm track)
      lastfm/
        __init__.py
        signing.py                  # api_sig MD5 signing (pure)
        client.py                   # LastfmClient: get_session, get_recent_tracks
      auth/
        __init__.py
        registration.py             # REGISTRATION_MODE allowlist check
        service.py                  # upsert_user_from_session (account create/login)
        session.py                  # signed session cookie encode/decode + current_user dep
      ingest/
        __init__.py
        repository.py               # upsert_listens (dedup), sync_state read/advance
        service.py                  # ingest_user, backfill_user
        poller.py                   # poll_all_users entrypoint
      stats/
        __init__.py
        queries.py                  # aggregation SQL (top lists, clock, totals, recent)
      routes/
        __init__.py
        auth.py                     # /auth/login, /auth/callback, /auth/logout
        stats.py                    # /stats/* (gated)
        share.py                    # /share create/revoke + public /shared/{token}
        health.py                   # /health
      deps.py                       # FastAPI dependencies (settings, db session, lastfm client)
      main.py                       # app factory, router wiring, lifespan
      cli.py                        # `tidalwave-poll`, `tidalwave-backfill` entrypoints
    tests/
      conftest.py                   # env isolation, async db engine, session fixtures
      ...                           # one test module per source module
```

---

## Phase 0 — Scaffolding

### Task 1: Project scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/.python-version`
- Create: `backend/docker-compose.yml`
- Create: `backend/src/tidalwave/__init__.py`
- Test: `backend/tests/test_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_smoke.py
def test_package_imports():
    import tidalwave

    assert tidalwave.__version__ == "0.1.0"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tidalwave'`

- [ ] **Step 3: Create the project files**

```toml
# backend/pyproject.toml
[project]
name = "tidalwave"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "httpx>=0.28",
    "pydantic-settings>=2.6",
    "itsdangerous>=2.2",
]

[project.scripts]
tidalwave-poll = "tidalwave.cli:poll"
tidalwave-backfill = "tidalwave.cli:backfill"

[dependency-groups]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "respx>=0.21",
    "ruff>=0.7",
    "mypy>=1.13",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-ra"

[tool.ruff]
line-length = 100
target-version = "py312"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/tidalwave"]
```

```
# backend/.python-version
3.12
```

```yaml
# backend/docker-compose.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: tidalwave
      POSTGRES_PASSWORD: tidalwave
      POSTGRES_DB: tidalwave
    ports:
      - "5432:5432"
```

```python
# backend/src/tidalwave/__init__.py
__version__ = "0.1.0"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv sync && uv run pytest tests/test_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add pyproject.toml .python-version docker-compose.yml src/tidalwave/__init__.py tests/test_smoke.py uv.lock
git commit -m "chore: scaffold tidalwave backend project"
```

---

## Phase 1 — Config & data model

### Task 2: Settings

**Files:**
- Create: `backend/src/tidalwave/config.py`
- Test: `backend/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_config.py
import pytest

from tidalwave.config import Settings


def test_defaults():
    s = Settings()
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert s.registration_mode == "allowlist"
    assert s.registration_allowlist == []


def test_allowlist_parses_csv(monkeypatch):
    monkeypatch.setenv("TIDALWAVE_REGISTRATION_ALLOWLIST", "alice, bob")
    s = Settings()
    assert s.registration_allowlist == ["alice", "bob"]


def test_invalid_registration_mode_rejected(monkeypatch):
    monkeypatch.setenv("TIDALWAVE_REGISTRATION_MODE", "nonsense")
    with pytest.raises(ValueError):
        Settings()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tidalwave.config'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/config.py
from typing import Annotated, Literal

from pydantic import Field, NoDecode, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration from env vars prefixed with `TIDALWAVE_`."""

    model_config = SettingsConfigDict(
        env_prefix="TIDALWAVE_",
        case_sensitive=False,
        populate_by_name=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://tidalwave:tidalwave@localhost:5432/tidalwave"

    lastfm_api_key: str = ""
    lastfm_api_secret: str = ""
    # Public base URL used to build the Last.fm callback (cb=) parameter.
    public_base_url: str = "http://localhost:8080"

    registration_mode: Literal["open", "allowlist"] = "allowlist"
    registration_allowlist: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # Secret used to sign the session cookie. MUST be overridden in production.
    session_secret: str = "dev-insecure-change-me"

    log_level: str = "INFO"

    @field_validator("registration_allowlist", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/config.py tests/test_config.py
git commit -m "feat: add Settings config"
```

---

### Task 3: ORM models

**Files:**
- Create: `backend/src/tidalwave/models/__init__.py` (empty)
- Create: `backend/src/tidalwave/models/db.py`
- Test: `backend/tests/models/test_db_models.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/models/test_db_models.py
from tidalwave.models.db import Base, Listen, Share, SyncState, User


def test_tables_registered():
    names = set(Base.metadata.tables)
    assert names == {"users", "listens", "sync_state", "shares"}


def test_listen_dedup_constraint_present():
    cols = {c.name for c in Listen.__table__.columns}
    assert {"user_id", "artist", "track_title", "played_at"} <= cols
    uniques = [c for c in Listen.__table__.constraints if c.__class__.__name__ == "UniqueConstraint"]
    assert any(
        {col.name for col in u.columns} == {"user_id", "artist", "track_title", "played_at"}
        for u in uniques
    )


def test_user_username_unique():
    assert User.__table__.columns["lastfm_username"].unique is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/models/test_db_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tidalwave.models.db'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/models/db.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lastfm_username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    lastfm_session_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    disconnected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Listen(Base):
    __tablename__ = "listens"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "artist", "track_title", "played_at", name="uq_listen_dedup"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    track_title: Mapped[str] = mapped_column(Text, nullable=False)
    artist: Mapped[str] = mapped_column(Text, nullable=False)
    album: Mapped[str | None] = mapped_column(Text)
    played_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    track_mbid: Mapped[str | None] = mapped_column(String(36))
    artist_mbid: Mapped[str | None] = mapped_column(String(36))
    album_mbid: Mapped[str | None] = mapped_column(String(36))


class SyncState(Base):
    __tablename__ = "sync_state"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    last_played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Share(Base):
    __tablename__ = "shares"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    share_token: Mapped[str] = mapped_column(String(43), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    range_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    range_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

```python
# backend/src/tidalwave/models/__init__.py
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/models/test_db_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/models/ tests/models/
git commit -m "feat: add ORM models (User, Listen, SyncState, Share)"
```

---

### Task 4: DB helpers + test fixtures + Alembic baseline

**Files:**
- Create: `backend/src/tidalwave/db.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/script.py.mako`
- Test: `backend/tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_db.py
from sqlalchemy import text

from tidalwave.models.db import User


async def test_session_can_insert_and_read(db_session):
    db_session.add(User(lastfm_username="alice", lastfm_session_key="sk"))
    await db_session.flush()
    row = (await db_session.execute(text("SELECT lastfm_username FROM users"))).scalar_one()
    assert row == "alice"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_db.py -v`
Expected: FAIL — fixture `db_session` not found.

- [ ] **Step 3: Write db helpers + conftest**

```python
# backend/src/tidalwave/db.py
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tidalwave.config import Settings


def make_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True, future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
```

```python
# backend/tests/conftest.py
import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tidalwave.models.db import Base

# Tests run against the docker-compose Postgres. Override via TIDALWAVE_TEST_DATABASE_URL.
TEST_DB_URL = os.environ.get(
    "TIDALWAVE_TEST_DATABASE_URL",
    "postgresql+asyncpg://tidalwave:tidalwave@localhost:5432/tidalwave",
)


@pytest.fixture(autouse=True)
def _isolate_env_file(tmp_path, monkeypatch):
    # pydantic-settings reads .env from CWD; keep tests from seeing local secrets.
    monkeypatch.chdir(tmp_path)


@pytest_asyncio.fixture(scope="session")
async def _engine():
    engine = create_async_engine(TEST_DB_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_engine):
    # Each test runs in a transaction rolled back at teardown — full isolation.
    connection = await _engine.connect()
    trans = await connection.begin()
    factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && docker-compose up -d && uv run pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 5: Initialize Alembic and autogenerate the baseline migration**

```bash
cd backend
uv run alembic init -t async migrations
```

Then edit `migrations/env.py` so autogenerate sees the metadata and URL — replace the
`target_metadata = None` line and the URL lookup:

```python
# migrations/env.py  (key edits)
from tidalwave.config import Settings
from tidalwave.models.db import Base

target_metadata = Base.metadata


def _url() -> str:
    return Settings().database_url


# in run_migrations_offline(): url = _url()
# in run_migrations_online(): set config section's sqlalchemy.url = _url() before engine creation
```

```bash
uv run alembic revision --autogenerate -m "baseline schema"
uv run alembic upgrade head
```

- [ ] **Step 6: Commit**

```bash
cd backend && git add src/tidalwave/db.py tests/conftest.py tests/test_db.py alembic.ini migrations/
git commit -m "feat: add db helpers, test fixtures, Alembic baseline"
```

---

## Phase 2 — Last.fm client

### Task 5: API signature (pure function)

**Files:**
- Create: `backend/src/tidalwave/lastfm/__init__.py` (empty)
- Create: `backend/src/tidalwave/lastfm/signing.py`
- Test: `backend/tests/lastfm/test_signing.py`

Last.fm `api_sig` = MD5 of all request params (except `format`/`callback`) sorted by name,
concatenated as `name+value`, with the shared secret appended. UTF-8 encoded.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/lastfm/test_signing.py
from tidalwave.lastfm.signing import sign


def test_sign_concatenates_sorted_params_plus_secret():
    # Worked example: params {b:2, a:1}, secret "S" ->
    # md5("a1b2S")
    import hashlib

    expected = hashlib.md5("a1b2S".encode("utf-8")).hexdigest()
    assert sign({"b": "2", "a": "1"}, secret="S") == expected


def test_sign_excludes_format_and_callback():
    import hashlib

    expected = hashlib.md5("a1S".encode("utf-8")).hexdigest()
    assert sign({"a": "1", "format": "json", "callback": "x"}, secret="S") == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lastfm/test_signing.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/lastfm/signing.py
from __future__ import annotations

import hashlib
from collections.abc import Mapping

_EXCLUDED = {"format", "callback"}


def sign(params: Mapping[str, str], *, secret: str) -> str:
    """Compute a Last.fm api_sig for the given request params."""
    parts = [f"{k}{params[k]}" for k in sorted(params) if k not in _EXCLUDED]
    raw = "".join(parts) + secret
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lastfm/test_signing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/lastfm/__init__.py src/tidalwave/lastfm/signing.py tests/lastfm/
git commit -m "feat: add Last.fm api_sig signing"
```

---

### Task 6: Last.fm client — `get_session`

**Files:**
- Create: `backend/src/tidalwave/models/domain.py`
- Create: `backend/src/tidalwave/lastfm/client.py`
- Test: `backend/tests/lastfm/test_client_session.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/lastfm/test_client_session.py
import httpx
import pytest
import respx

from tidalwave.lastfm.client import LastfmClient, LastfmError


@pytest.fixture
async def client():
    async with httpx.AsyncClient() as http:
        yield LastfmClient(http, api_key="KEY", api_secret="SECRET")


@respx.mock
async def test_get_session_returns_username_and_key(client):
    respx.get("https://ws.audioscrobbler.com/2.0/").respond(
        json={"session": {"name": "alice", "key": "SESS123", "subscriber": 0}}
    )
    result = await client.get_session("TOKEN")
    assert result == ("alice", "SESS123")


@respx.mock
async def test_get_session_raises_on_lastfm_error(client):
    respx.get("https://ws.audioscrobbler.com/2.0/").respond(
        json={"error": 14, "message": "Unauthorized Token"}
    )
    with pytest.raises(LastfmError):
        await client.get_session("BADTOKEN")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/lastfm/test_client_session.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write domain dataclass + client**

```python
# backend/src/tidalwave/models/domain.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Scrobble:
    """A single parsed Last.fm listen. `played_at` is None for a now-playing track."""

    artist: str
    track_title: str
    album: str | None
    played_at: datetime | None
    track_mbid: str | None = None
    artist_mbid: str | None = None
    album_mbid: str | None = None

    @property
    def now_playing(self) -> bool:
        return self.played_at is None
```

```python
# backend/src/tidalwave/lastfm/client.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from tidalwave.lastfm.signing import sign
from tidalwave.models.domain import Scrobble

_API = "https://ws.audioscrobbler.com/2.0/"


@dataclass(frozen=True, slots=True)
class LastfmError(Exception):
    code: int
    message: str

    def __str__(self) -> str:
        return f"Last.fm error {self.code}: {self.message}"


@dataclass(frozen=True, slots=True)
class RecentTracksPage:
    scrobbles: list[Scrobble]
    page: int
    total_pages: int


class LastfmClient:
    def __init__(self, http: httpx.AsyncClient, *, api_key: str, api_secret: str) -> None:
        self._http = http
        self._key = api_key
        self._secret = api_secret

    async def _call(self, params: dict[str, str], *, signed: bool) -> dict:
        q = {**params, "api_key": self._key, "format": "json"}
        if signed:
            q["api_sig"] = sign({**params, "api_key": self._key}, secret=self._secret)
        resp = await self._http.get(_API, params=q)
        data = resp.json()
        if "error" in data:
            raise LastfmError(int(data["error"]), data.get("message", ""))
        resp.raise_for_status()
        return data

    async def get_session(self, token: str) -> tuple[str, str]:
        """Exchange an auth token for (username, session_key)."""
        data = await self._call(
            {"method": "auth.getSession", "token": token}, signed=True
        )
        session = data["session"]
        return session["name"], session["key"]

    async def get_recent_tracks(
        self, username: str, *, from_ts: int | None = None, page: int = 1, limit: int = 200
    ) -> RecentTracksPage:
        params = {
            "method": "user.getRecentTracks",
            "user": username,
            "limit": str(limit),
            "page": str(page),
            "extended": "0",
        }
        if from_ts is not None:
            params["from"] = str(from_ts)
        data = await self._call(params, signed=False)
        return _parse_recent_tracks(data)


def _parse_recent_tracks(data: dict) -> RecentTracksPage:
    block = data["recenttracks"]
    attr = block["@attr"]
    raw = block.get("track", [])
    if isinstance(raw, dict):  # Last.fm returns a bare object for a single track
        raw = [raw]
    scrobbles = [_parse_track(t) for t in raw]
    return RecentTracksPage(
        scrobbles=scrobbles,
        page=int(attr["page"]),
        total_pages=int(attr["totalPages"]),
    )


def _parse_track(t: dict) -> Scrobble:
    now_playing = t.get("@attr", {}).get("nowplaying") == "true"
    played_at: datetime | None = None
    if not now_playing and "date" in t:
        played_at = datetime.fromtimestamp(int(t["date"]["uts"]), tz=UTC)
    album = t.get("album", {}).get("#text") or None
    return Scrobble(
        artist=t["artist"]["#text"],
        track_title=t["name"],
        album=album,
        played_at=played_at,
        track_mbid=t.get("mbid") or None,
        artist_mbid=t.get("artist", {}).get("mbid") or None,
        album_mbid=t.get("album", {}).get("mbid") or None,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/lastfm/test_client_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/lastfm/client.py src/tidalwave/models/domain.py tests/lastfm/test_client_session.py
git commit -m "feat: add LastfmClient.get_session + Scrobble domain type"
```

---

### Task 7: Last.fm client — `get_recent_tracks` parsing

**Files:**
- Modify: (none — implemented in Task 6)
- Create: `backend/tests/fixtures/recent_tracks_page1.json`
- Test: `backend/tests/lastfm/test_client_recent.py`

- [ ] **Step 1: Create the fixture**

```json
// backend/tests/fixtures/recent_tracks_page1.json
{
  "recenttracks": {
    "@attr": { "user": "alice", "page": "1", "perPage": "200", "totalPages": "2", "total": "201" },
    "track": [
      {
        "artist": { "#text": "Kavinsky", "mbid": "a1" },
        "name": "Nightcall",
        "album": { "#text": "OutRun", "mbid": "b1" },
        "mbid": "c1",
        "@attr": { "nowplaying": "true" }
      },
      {
        "artist": { "#text": "Daft Punk", "mbid": "a2" },
        "name": "Aerodynamic",
        "album": { "#text": "Discovery", "mbid": "" },
        "mbid": "",
        "date": { "uts": "1700000000", "#text": "14 Nov 2023, 22:13" }
      }
    ]
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/lastfm/test_client_recent.py
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
import respx

from tidalwave.lastfm.client import LastfmClient

FIX = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
async def client():
    async with httpx.AsyncClient() as http:
        yield LastfmClient(http, api_key="KEY", api_secret="SECRET")


@respx.mock
async def test_parses_recent_tracks_and_nowplaying(client):
    payload = json.loads((FIX / "recent_tracks_page1.json").read_text())
    respx.get("https://ws.audioscrobbler.com/2.0/").respond(json=payload)

    page = await client.get_recent_tracks("alice", page=1)

    assert page.page == 1
    assert page.total_pages == 2
    assert len(page.scrobbles) == 2

    np = page.scrobbles[0]
    assert np.now_playing is True
    assert np.played_at is None
    assert np.track_title == "Nightcall"

    done = page.scrobbles[1]
    assert done.now_playing is False
    assert done.played_at == datetime.fromtimestamp(1700000000, tz=UTC)
    assert done.artist == "Daft Punk"
    assert done.album == "Discovery"
    assert done.album_mbid is None  # empty string normalized to None
```

- [ ] **Step 3: Run test to verify it passes** (parsing already implemented in Task 6)

Run: `cd backend && uv run pytest tests/lastfm/test_client_recent.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd backend && git add tests/lastfm/test_client_recent.py tests/fixtures/recent_tracks_page1.json
git commit -m "test: cover get_recent_tracks parsing + now-playing handling"
```

---

## Phase 3 — Auth / connect flow

### Task 8: Registration allowlist check

**Files:**
- Create: `backend/src/tidalwave/auth/__init__.py` (empty)
- Create: `backend/src/tidalwave/auth/registration.py`
- Test: `backend/tests/auth/test_registration.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/auth/test_registration.py
import pytest

from tidalwave.auth.registration import RegistrationDenied, ensure_allowed


def test_open_mode_allows_anyone():
    ensure_allowed("alice", mode="open", allowlist=[])  # no exception


def test_allowlist_allows_listed_user_case_insensitive():
    ensure_allowed("Alice", mode="allowlist", allowlist=["alice"])


def test_allowlist_denies_unlisted_user():
    with pytest.raises(RegistrationDenied):
        ensure_allowed("mallory", mode="allowlist", allowlist=["alice"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/auth/test_registration.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/auth/registration.py
from __future__ import annotations


class RegistrationDenied(Exception):
    pass


def ensure_allowed(username: str, *, mode: str, allowlist: list[str]) -> None:
    if mode == "open":
        return
    lowered = {u.lower() for u in allowlist}
    if username.lower() not in lowered:
        raise RegistrationDenied(username)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/auth/test_registration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/auth/__init__.py src/tidalwave/auth/registration.py tests/auth/
git commit -m "feat: add registration allowlist check"
```

---

### Task 9: User upsert (connect = create-or-login)

**Files:**
- Create: `backend/src/tidalwave/auth/service.py`
- Test: `backend/tests/auth/test_service.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/auth/test_service.py
import pytest
from sqlalchemy import func, select

from tidalwave.auth.registration import RegistrationDenied
from tidalwave.auth.service import upsert_user_from_session
from tidalwave.models.db import User


async def test_first_user_becomes_admin(db_session):
    user = await upsert_user_from_session(
        db_session, "alice", "sk1", mode="open", allowlist=[]
    )
    assert user.is_admin is True
    assert user.lastfm_session_key == "sk1"


async def test_existing_user_is_logged_in_and_key_refreshed(db_session):
    first = await upsert_user_from_session(db_session, "alice", "sk1", mode="open", allowlist=[])
    again = await upsert_user_from_session(db_session, "alice", "sk2", mode="open", allowlist=[])
    assert again.id == first.id
    assert again.lastfm_session_key == "sk2"
    assert again.disconnected is False
    count = (await db_session.execute(select(func.count()).select_from(User))).scalar_one()
    assert count == 1


async def test_second_user_not_admin(db_session):
    await upsert_user_from_session(db_session, "alice", "sk1", mode="open", allowlist=[])
    bob = await upsert_user_from_session(db_session, "bob", "sk2", mode="open", allowlist=[])
    assert bob.is_admin is False


async def test_new_user_denied_when_not_on_allowlist(db_session):
    with pytest.raises(RegistrationDenied):
        await upsert_user_from_session(
            db_session, "mallory", "sk", mode="allowlist", allowlist=["alice"]
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/auth/test_service.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/auth/service.py
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.auth.registration import ensure_allowed
from tidalwave.models.db import User


async def upsert_user_from_session(
    session: AsyncSession,
    username: str,
    session_key: str,
    *,
    mode: str,
    allowlist: list[str],
) -> User:
    """Create the user (first connect) or refresh an existing user's session key."""
    existing = (
        await session.execute(select(User).where(User.lastfm_username == username))
    ).scalar_one_or_none()
    if existing is not None:
        existing.lastfm_session_key = session_key
        existing.disconnected = False
        await session.flush()
        return existing

    ensure_allowed(username, mode=mode, allowlist=allowlist)
    is_first = (await session.execute(select(func.count()).select_from(User))).scalar_one() == 0
    user = User(
        lastfm_username=username,
        lastfm_session_key=session_key,
        is_admin=is_first,
    )
    session.add(user)
    await session.flush()
    return user
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/auth/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/auth/service.py tests/auth/test_service.py
git commit -m "feat: add connect = create-or-login user upsert"
```

---

### Task 10: Session cookie + current_user dependency

**Files:**
- Create: `backend/src/tidalwave/auth/session.py`
- Test: `backend/tests/auth/test_session.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/auth/test_session.py
import pytest

from tidalwave.auth.session import SessionCodec


def test_roundtrip_encodes_and_decodes_user_id():
    codec = SessionCodec(secret="s3cr3t")
    token = codec.encode(42)
    assert codec.decode(token) == 42


def test_tampered_token_rejected():
    codec = SessionCodec(secret="s3cr3t")
    assert codec.decode("garbage.value.here") is None


def test_token_signed_with_other_secret_rejected():
    token = SessionCodec(secret="A").encode(1)
    assert SessionCodec(secret="B").decode(token) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/auth/test_session.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/auth/session.py
from __future__ import annotations

from itsdangerous import BadSignature, URLSafeSerializer

COOKIE_NAME = "tw_session"


class SessionCodec:
    def __init__(self, secret: str) -> None:
        self._s = URLSafeSerializer(secret, salt="tidalwave-session")

    def encode(self, user_id: int) -> str:
        return self._s.dumps({"uid": user_id})

    def decode(self, token: str) -> int | None:
        try:
            data = self._s.loads(token)
        except BadSignature:
            return None
        uid = data.get("uid")
        return uid if isinstance(uid, int) else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/auth/test_session.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/auth/session.py tests/auth/test_session.py
git commit -m "feat: add signed session cookie codec"
```

---

## Phase 4 — Ingest & backfill

### Task 11: Listen dedup upsert + sync_state repository

**Files:**
- Create: `backend/src/tidalwave/ingest/__init__.py` (empty)
- Create: `backend/src/tidalwave/ingest/repository.py`
- Test: `backend/tests/ingest/test_repository.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/ingest/test_repository.py
from datetime import UTC, datetime

from sqlalchemy import func, select

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.repository import (
    advance_sync_state,
    get_sync_state,
    upsert_listens,
)
from tidalwave.models.db import Listen
from tidalwave.models.domain import Scrobble


def _scrobble(title: str, ts: int) -> Scrobble:
    return Scrobble(
        artist="A", track_title=title, album="Alb",
        played_at=datetime.fromtimestamp(ts, tz=UTC),
    )


async def test_upsert_inserts_and_dedups(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    s = [_scrobble("t1", 1000), _scrobble("t2", 2000)]

    inserted = await upsert_listens(db_session, user.id, s)
    assert inserted == 2

    # Re-inserting the same scrobbles plus one new one only adds the new one.
    inserted2 = await upsert_listens(db_session, user.id, [*s, _scrobble("t3", 3000)])
    assert inserted2 == 1

    total = (
        await db_session.execute(select(func.count()).select_from(Listen))
    ).scalar_one()
    assert total == 3


async def test_now_playing_scrobbles_are_skipped(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    np = Scrobble(artist="A", track_title="np", album=None, played_at=None)
    inserted = await upsert_listens(db_session, user.id, [np])
    assert inserted == 0


async def test_sync_state_roundtrip(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    assert await get_sync_state(db_session, user.id) is None

    ts = datetime.fromtimestamp(5000, tz=UTC)
    await advance_sync_state(db_session, user.id, last_played_at=ts)
    state = await get_sync_state(db_session, user.id)
    assert state is not None and state.last_played_at == ts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/ingest/test_repository.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/ingest/repository.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.models.db import Listen, SyncState
from tidalwave.models.domain import Scrobble


async def upsert_listens(
    session: AsyncSession, user_id: int, scrobbles: list[Scrobble]
) -> int:
    """Insert finished scrobbles, skipping now-playing and duplicates. Returns inserted count."""
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
        if not s.now_playing
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
        .values(user_id=user_id, last_played_at=last_played_at, last_synced_at=func_now())
        .on_conflict_do_update(
            index_elements=[SyncState.user_id],
            set_={"last_played_at": last_played_at, "last_synced_at": func_now()},
        )
    )
    await session.execute(stmt)


def func_now():
    from sqlalchemy import func

    return func.now()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/ingest/test_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/ingest/__init__.py src/tidalwave/ingest/repository.py tests/ingest/
git commit -m "feat: add listen dedup upsert + sync_state repository"
```

---

### Task 12: Ingest service (incremental)

**Files:**
- Create: `backend/src/tidalwave/ingest/service.py`
- Test: `backend/tests/ingest/test_service.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/ingest/test_service.py
from datetime import UTC, datetime

from sqlalchemy import select

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.repository import get_sync_state
from tidalwave.ingest.service import ingest_user
from tidalwave.lastfm.client import RecentTracksPage
from tidalwave.models.db import Listen
from tidalwave.models.domain import Scrobble


class FakeClient:
    """Returns preconfigured pages keyed by requested page number."""

    def __init__(self, pages: dict[int, RecentTracksPage]) -> None:
        self.pages = pages
        self.calls: list[tuple[str, int | None, int]] = []

    async def get_recent_tracks(self, username, *, from_ts=None, page=1, limit=200):
        self.calls.append((username, from_ts, page))
        return self.pages[page]


def _sc(title: str, ts: int) -> Scrobble:
    return Scrobble(artist="A", track_title=title, album=None,
                    played_at=datetime.fromtimestamp(ts, tz=UTC))


async def test_ingest_walks_all_pages_and_advances_state(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    client = FakeClient({
        1: RecentTracksPage([_sc("t3", 3000), _sc("t2", 2000)], page=1, total_pages=2),
        2: RecentTracksPage([_sc("t1", 1000)], page=2, total_pages=2),
    })

    inserted = await ingest_user(db_session, client, user)

    assert inserted == 3
    listens = (await db_session.execute(select(Listen))).scalars().all()
    assert {l.track_title for l in listens} == {"t1", "t2", "t3"}
    state = await get_sync_state(db_session, user.id)
    assert state.last_played_at == datetime.fromtimestamp(3000, tz=UTC)  # newest


async def test_ingest_uses_from_ts_after_first_run(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    client = FakeClient({1: RecentTracksPage([_sc("t1", 1000)], page=1, total_pages=1)})
    await ingest_user(db_session, client, user)

    client2 = FakeClient({1: RecentTracksPage([_sc("t2", 2000)], page=1, total_pages=1)})
    await ingest_user(db_session, client2, user)
    # second run should request from just after the last stored timestamp
    assert client2.calls[0][1] == 1001
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/ingest/test_service.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/ingest/service.py
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
        collected.extend(s for s in result.scrobbles if not s.now_playing)
        page += 1

    inserted = await upsert_listens(session, user.id, collected)

    newest = max((s.played_at for s in collected if s.played_at), default=None)
    if newest is not None:
        await advance_sync_state(session, user.id, last_played_at=newest)
    return inserted
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/ingest/test_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/ingest/service.py tests/ingest/test_service.py
git commit -m "feat: add incremental ingest service"
```

---

### Task 13: Backfill = ingest with no sync floor

**Files:**
- Modify: `backend/src/tidalwave/ingest/service.py`
- Test: `backend/tests/ingest/test_backfill.py`

The backfill is the same page-walking logic without a `from_ts` floor, run once. Implement
it as a thin wrapper so behaviour stays DRY.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/ingest/test_backfill.py
from datetime import UTC, datetime

from sqlalchemy import func, select

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.service import backfill_user
from tidalwave.lastfm.client import RecentTracksPage
from tidalwave.models.db import Listen
from tidalwave.models.domain import Scrobble


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def get_recent_tracks(self, username, *, from_ts=None, page=1, limit=200):
        self.calls.append((from_ts, page))
        return self.pages[page]


def _sc(title, ts):
    return Scrobble(artist="A", track_title=title, album=None,
                    played_at=datetime.fromtimestamp(ts, tz=UTC))


async def test_backfill_ignores_sync_floor_and_is_idempotent(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    pages = {1: RecentTracksPage([_sc("t1", 1000)], page=1, total_pages=1)}

    await backfill_user(db_session, FakeClient(pages), user)
    again = await backfill_user(db_session, FakeClient(pages), user)

    assert again == 0  # idempotent
    total = (await db_session.execute(select(func.count()).select_from(Listen))).scalar_one()
    assert total == 1
    # backfill never sends a `from` floor
    assert FakeClient(pages).calls == []  # sanity: new instance has no calls
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/ingest/test_backfill.py -v`
Expected: FAIL — `backfill_user` not defined.

- [ ] **Step 3: Refactor ingest_user to share a page-walk + add backfill_user**

Replace the body of `ingest_user` and add `backfill_user`, both delegating to a private
`_collect_and_store` that takes an explicit `from_ts`:

```python
# backend/src/tidalwave/ingest/service.py  (replace ingest_user, add helpers)
async def ingest_user(session: AsyncSession, client: RecentTracksSource, user: User) -> int:
    state = await get_sync_state(session, user.id)
    from_ts: int | None = None
    if state is not None and state.last_played_at is not None:
        from_ts = int(state.last_played_at.timestamp()) + 1
    return await _collect_and_store(session, client, user, from_ts=from_ts)


async def backfill_user(session: AsyncSession, client: RecentTracksSource, user: User) -> int:
    """Import the full history (no sync floor). Idempotent via the dedup constraint."""
    return await _collect_and_store(session, client, user, from_ts=None)


async def _collect_and_store(
    session: AsyncSession, client: RecentTracksSource, user: User, *, from_ts: int | None
) -> int:
    collected: list[Scrobble] = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        result = await client.get_recent_tracks(user.lastfm_username, from_ts=from_ts, page=page)
        total_pages = result.total_pages
        collected.extend(s for s in result.scrobbles if not s.now_playing)
        page += 1

    inserted = await upsert_listens(session, user.id, collected)
    newest = max((s.played_at for s in collected if s.played_at), default=None)
    if newest is not None:
        await advance_sync_state(session, user.id, last_played_at=newest)
    return inserted
```

- [ ] **Step 4: Run all ingest tests to verify they pass**

Run: `cd backend && uv run pytest tests/ingest/ -v`
Expected: PASS (Task 12 tests still green after refactor)

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/ingest/service.py tests/ingest/test_backfill.py
git commit -m "feat: add backfill via shared page-walk"
```

---

### Task 14: Poller (iterate connected users)

**Files:**
- Create: `backend/src/tidalwave/ingest/poller.py`
- Test: `backend/tests/ingest/test_poller.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/ingest/test_poller.py
from datetime import UTC, datetime

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.poller import poll_all_users
from tidalwave.lastfm.client import LastfmError, RecentTracksPage
from tidalwave.models.domain import Scrobble


class FakeClient:
    def __init__(self, by_user):
        self.by_user = by_user

    async def get_recent_tracks(self, username, *, from_ts=None, page=1, limit=200):
        if username == "boom":
            raise LastfmError(8, "operation failed")
        return self.by_user[username]


def _page(ts):
    return RecentTracksPage(
        [Scrobble(artist="A", track_title="t", album=None,
                  played_at=datetime.fromtimestamp(ts, tz=UTC))],
        page=1, total_pages=1,
    )


async def test_poll_processes_every_connected_user_and_isolates_failures(db_session):
    await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    boom = await upsert_user_from_session(db_session, "boom", "sk", mode="open", allowlist=[])
    boom.disconnected = False
    skipped = await upsert_user_from_session(db_session, "carol", "sk", mode="open", allowlist=[])
    skipped.disconnected = True
    await db_session.flush()

    client = FakeClient({"alice": _page(1000), "carol": _page(1000)})
    report = await poll_all_users(db_session, client)

    assert report["alice"] == 1
    assert report["boom"] == "error"   # failure isolated, not raised
    assert "carol" not in report        # disconnected users skipped
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/ingest/test_poller.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/ingest/poller.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/ingest/test_poller.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/ingest/poller.py tests/ingest/test_poller.py
git commit -m "feat: add poller over connected users with failure isolation"
```

---

## Phase 5 — Stats

### Task 15: Stats queries

**Files:**
- Create: `backend/src/tidalwave/stats/__init__.py` (empty)
- Create: `backend/src/tidalwave/stats/queries.py`
- Test: `backend/tests/stats/test_queries.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/stats/test_queries.py
from datetime import UTC, datetime

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.repository import upsert_listens
from tidalwave.models.domain import Scrobble
from tidalwave.stats.queries import (
    listening_clock,
    top_artists,
    total_listens,
)


def _sc(artist, title, ts):
    return Scrobble(artist=artist, track_title=title, album=None,
                    played_at=datetime.fromtimestamp(ts, tz=UTC))


async def _seed(db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    # 2 Daft Punk, 1 Kavinsky; timestamps at hour 0 UTC (ts multiples of 86400)
    await upsert_listens(db_session, user.id, [
        _sc("Daft Punk", "a", 0),
        _sc("Daft Punk", "b", 86400),
        _sc("Kavinsky", "c", 172800),
    ])
    return user


async def test_top_artists_ranks_by_count(db_session):
    user = await _seed(db_session)
    rows = await top_artists(db_session, user.id, limit=10)
    assert rows[0] == {"artist": "Daft Punk", "count": 2}
    assert rows[1] == {"artist": "Kavinsky", "count": 1}


async def test_total_listens(db_session):
    user = await _seed(db_session)
    assert await total_listens(db_session, user.id) == 3


async def test_listening_clock_buckets_by_hour(db_session):
    user = await _seed(db_session)
    clock = await listening_clock(db_session, user.id)
    assert clock[0] == 3  # all three at UTC hour 0
    assert len(clock) == 24


async def test_top_artists_isolated_per_user(db_session):
    await _seed(db_session)
    bob = await upsert_user_from_session(db_session, "bob", "sk", mode="open", allowlist=[])
    assert await top_artists(db_session, bob.id, limit=10) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/stats/test_queries.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/stats/queries.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, cast, func, select
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


async def listening_clock(session: AsyncSession, user_id: int, *,
                          since=None, until=None) -> list[int]:
    """Returns a 24-element list: listens per UTC hour-of-day."""
    hour = cast(func.extract("hour", Listen.played_at), Integer)
    stmt = _scope(select(hour, func.count()), user_id, since, until).group_by(hour)
    counts = {int(h): int(c) for h, c in (await session.execute(stmt)).all()}
    return [counts.get(h, 0) for h in range(24)]


async def recent_listens(session: AsyncSession, user_id: int, *, limit: int = 50) -> list[dict]:
    stmt = (
        select(Listen.track_title, Listen.artist, Listen.album, Listen.played_at)
        .where(Listen.user_id == user_id)
        .order_by(Listen.played_at.desc())
        .limit(limit)
    )
    return [
        {"track": r[0], "artist": r[1], "album": r[2], "played_at": r[3].isoformat()}
        for r in (await session.execute(stmt)).all()
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/stats/test_queries.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/stats/ tests/stats/
git commit -m "feat: add stats aggregation queries"
```

---

## Phase 6 — App wiring, routes, sharing

### Task 16: Dependencies + app factory + health route

**Files:**
- Create: `backend/src/tidalwave/deps.py`
- Create: `backend/src/tidalwave/routes/__init__.py` (empty)
- Create: `backend/src/tidalwave/routes/health.py`
- Create: `backend/src/tidalwave/main.py`
- Test: `backend/tests/routes/test_health.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/routes/test_health.py
import httpx
import pytest

from tidalwave.main import create_app


@pytest.fixture
async def app_client(_engine, monkeypatch):
    monkeypatch.setenv("TIDALWAVE_DATABASE_URL", str(_engine.url).replace("***", "tidalwave"))
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_ok(app_client):
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_health.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write deps, health route, app factory**

```python
# backend/src/tidalwave/deps.py
from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.config import Settings


@lru_cache
def get_settings() -> Settings:
    return Settings()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session
        await session.commit()
```

```python
# backend/src/tidalwave/routes/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

```python
# backend/src/tidalwave/main.py
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from tidalwave.db import make_engine, make_session_factory
from tidalwave.deps import get_settings
from tidalwave.routes import health


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings)
        app.state.engine = engine
        app.state.session_factory = make_session_factory(engine)
        yield
        await engine.dispose()

    app = FastAPI(title="tidalwave", lifespan=lifespan)
    app.include_router(health.router)
    return app


app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/routes/test_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/deps.py src/tidalwave/routes/__init__.py src/tidalwave/routes/health.py src/tidalwave/main.py tests/routes/
git commit -m "feat: add app factory, deps, health route"
```

---

### Task 17: Auth routes (login redirect, callback, logout)

**Files:**
- Create: `backend/src/tidalwave/routes/auth.py`
- Modify: `backend/src/tidalwave/main.py` (include router + lifespan http client)
- Test: `backend/tests/routes/test_auth_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/routes/test_auth_routes.py
import httpx
import pytest
import respx

from tidalwave.auth.session import COOKIE_NAME, SessionCodec
from tidalwave.main import create_app


@pytest.fixture
async def app_client(_engine, monkeypatch):
    monkeypatch.setenv("TIDALWAVE_DATABASE_URL", str(_engine.url).replace("***", "tidalwave"))
    monkeypatch.setenv("TIDALWAVE_LASTFM_API_KEY", "KEY")
    monkeypatch.setenv("TIDALWAVE_LASTFM_API_SECRET", "SECRET")
    monkeypatch.setenv("TIDALWAVE_SESSION_SECRET", "test-secret")
    monkeypatch.setenv("TIDALWAVE_REGISTRATION_MODE", "open")
    monkeypatch.setenv("TIDALWAVE_PUBLIC_BASE_URL", "http://test")
    from tidalwave.deps import get_settings
    get_settings.cache_clear()
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_login_redirects_to_lastfm(app_client):
    resp = await app_client.get("/auth/login", follow_redirects=False)
    assert resp.status_code == 307
    loc = resp.headers["location"]
    assert loc.startswith("https://www.last.fm/api/auth/")
    assert "api_key=KEY" in loc
    assert "cb=http://test/auth/callback" in loc


@respx.mock
async def test_callback_creates_user_and_sets_cookie(app_client):
    respx.get("https://ws.audioscrobbler.com/2.0/").respond(
        json={"session": {"name": "alice", "key": "SESS", "subscriber": 0}}
    )
    resp = await app_client.get("/auth/callback?token=TOK", follow_redirects=False)
    assert resp.status_code == 307
    cookie = resp.cookies[COOKIE_NAME]
    assert SessionCodec("test-secret").decode(cookie) is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_auth_routes.py -v`
Expected: FAIL — `/auth/login` not found (404).

- [ ] **Step 3: Add a shared http client to lifespan, then write auth routes**

In `main.py` lifespan, add an httpx client to app state and include the auth router:

```python
# backend/src/tidalwave/main.py  (lifespan additions)
import httpx
from tidalwave.routes import auth, health
# inside lifespan, after session_factory:
        app.state.http = httpx.AsyncClient(timeout=15.0)
        yield
        await app.state.http.aclose()
        await engine.dispose()
# after creating app:
    app.include_router(health.router)
    app.include_router(auth.router)
```

```python
# backend/src/tidalwave/routes/auth.py
from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.auth.registration import RegistrationDenied
from tidalwave.auth.service import upsert_user_from_session
from tidalwave.auth.session import COOKIE_NAME, SessionCodec
from tidalwave.config import Settings
from tidalwave.deps import get_session, get_settings
from tidalwave.lastfm.client import LastfmClient, LastfmError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login")
async def login(settings: Settings = Depends(get_settings)) -> RedirectResponse:
    cb = f"{settings.public_base_url}/auth/callback"
    url = "https://www.last.fm/api/auth/?" + urlencode(
        {"api_key": settings.lastfm_api_key, "cb": cb}
    )
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    client = LastfmClient(
        request.app.state.http,
        api_key=settings.lastfm_api_key,
        api_secret=settings.lastfm_api_secret,
    )
    try:
        username, session_key = await client.get_session(token)
    except LastfmError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    try:
        user = await upsert_user_from_session(
            session, username, session_key,
            mode=settings.registration_mode, allowlist=settings.registration_allowlist,
        )
    except RegistrationDenied as e:
        raise HTTPException(status_code=403, detail="Registration not allowed") from e

    codec = SessionCodec(settings.session_secret)
    resp = RedirectResponse("/", status_code=307)
    resp.set_cookie(
        COOKIE_NAME, codec.encode(user.id), httponly=True, samesite="lax",
        secure=settings.public_base_url.startswith("https"),
    )
    return resp


@router.post("/logout")
async def logout() -> Response:
    resp = Response(status_code=204)
    resp.delete_cookie(COOKIE_NAME)
    return resp
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/routes/test_auth_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/routes/auth.py src/tidalwave/main.py tests/routes/test_auth_routes.py
git commit -m "feat: add Last.fm connect auth routes"
```

---

### Task 18: current_user dependency + gated stats routes

**Files:**
- Modify: `backend/src/tidalwave/auth/session.py` (add `current_user` dependency)
- Create: `backend/src/tidalwave/routes/stats.py`
- Modify: `backend/src/tidalwave/main.py` (include stats router)
- Test: `backend/tests/routes/test_stats_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/routes/test_stats_routes.py
import httpx
import pytest

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.auth.session import COOKIE_NAME, SessionCodec
from tidalwave.ingest.repository import upsert_listens
from tidalwave.main import create_app
from tidalwave.models.domain import Scrobble
from datetime import UTC, datetime


@pytest.fixture
async def app_client(_engine, monkeypatch):
    monkeypatch.setenv("TIDALWAVE_DATABASE_URL", str(_engine.url).replace("***", "tidalwave"))
    monkeypatch.setenv("TIDALWAVE_SESSION_SECRET", "test-secret")
    from tidalwave.deps import get_settings
    get_settings.cache_clear()
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_stats_requires_auth(app_client):
    resp = await app_client.get("/stats/top-artists")
    assert resp.status_code == 401


async def test_stats_returns_own_data(app_client, db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    await upsert_listens(db_session, user.id, [
        Scrobble(artist="Daft Punk", track_title="a", album=None,
                 played_at=datetime.fromtimestamp(0, tz=UTC)),
    ])
    await db_session.commit()

    cookie = SessionCodec("test-secret").encode(user.id)
    resp = await app_client.get("/stats/top-artists", cookies={COOKIE_NAME: cookie})
    assert resp.status_code == 200
    assert resp.json()[0] == {"artist": "Daft Punk", "count": 1}
```

> **Note for implementer:** `db_session` (rollback-per-test) and the ASGI app use separate
> connections, so this test commits its seed data. Ensure the `_engine` fixture and the
> app point at the same database (the conftest test URL).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_stats_routes.py -v`
Expected: FAIL — `/stats/top-artists` not found.

- [ ] **Step 3: Add current_user dependency + stats routes**

```python
# backend/src/tidalwave/auth/session.py  (append)
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tidalwave.deps import get_session, get_settings
from tidalwave.models.db import User


async def current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings=Depends(get_settings),
) -> User:
    token = request.cookies.get(COOKIE_NAME)
    uid = SessionCodec(settings.session_secret).decode(token) if token else None
    user = await session.get(User, uid) if uid is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
```

```python
# backend/src/tidalwave/routes/stats.py
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
```

Include the router in `main.py`:

```python
# backend/src/tidalwave/main.py
from tidalwave.routes import auth, health, stats
# ...
    app.include_router(stats.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/routes/test_stats_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/auth/session.py src/tidalwave/routes/stats.py src/tidalwave/main.py tests/routes/test_stats_routes.py
git commit -m "feat: add current_user dep + gated stats routes"
```

---

### Task 19: Sharing (create/revoke + public read-only view)

**Files:**
- Create: `backend/src/tidalwave/routes/share.py`
- Modify: `backend/src/tidalwave/main.py` (include share router)
- Test: `backend/tests/routes/test_share_routes.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/routes/test_share_routes.py
import httpx
import pytest
from datetime import UTC, datetime

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.auth.session import COOKIE_NAME, SessionCodec
from tidalwave.ingest.repository import upsert_listens
from tidalwave.main import create_app
from tidalwave.models.domain import Scrobble


@pytest.fixture
async def app_client(_engine, monkeypatch):
    monkeypatch.setenv("TIDALWAVE_DATABASE_URL", str(_engine.url).replace("***", "tidalwave"))
    monkeypatch.setenv("TIDALWAVE_SESSION_SECRET", "test-secret")
    from tidalwave.deps import get_settings
    get_settings.cache_clear()
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_share_create_then_public_view(app_client, db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    await upsert_listens(db_session, user.id, [
        Scrobble(artist="Kavinsky", track_title="Nightcall", album=None,
                 played_at=datetime.fromtimestamp(0, tz=UTC)),
    ])
    await db_session.commit()
    cookie = SessionCodec("test-secret").encode(user.id)

    created = await app_client.post("/shares", cookies={COOKIE_NAME: cookie})
    assert created.status_code == 201
    token = created.json()["share_token"]

    # public, no cookie
    view = await app_client.get(f"/shared/{token}/top-artists")
    assert view.status_code == 200
    assert view.json()[0] == {"artist": "Kavinsky", "count": 1}


async def test_revoked_share_returns_404(app_client, db_session):
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    await db_session.commit()
    cookie = SessionCodec("test-secret").encode(user.id)
    token = (await app_client.post("/shares", cookies={COOKIE_NAME: cookie})).json()["share_token"]

    await app_client.delete(f"/shares/{token}", cookies={COOKIE_NAME: cookie})
    view = await app_client.get(f"/shared/{token}/top-artists")
    assert view.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_share_routes.py -v`
Expected: FAIL — `/shares` not found.

- [ ] **Step 3: Write share routes**

```python
# backend/src/tidalwave/routes/share.py
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
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
    from sqlalchemy import func, update

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
```

Include in `main.py`:

```python
# backend/src/tidalwave/main.py
from tidalwave.routes import auth, health, share, stats
# ...
    app.include_router(share.router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/routes/test_share_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend && git add src/tidalwave/routes/share.py src/tidalwave/main.py tests/routes/test_share_routes.py
git commit -m "feat: add shareable read-only stats links"
```

---

### Task 20: CLI entrypoints (poll, backfill)

**Files:**
- Create: `backend/src/tidalwave/cli.py`
- Test: `backend/tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_cli.py
from tidalwave import cli


def test_cli_exposes_poll_and_backfill_entrypoints():
    assert callable(cli.poll)
    assert callable(cli.backfill)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_cli.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/src/tidalwave/cli.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite + commit**

Run: `cd backend && docker-compose up -d && uv run pytest -v`
Expected: ALL PASS

```bash
cd backend && git add src/tidalwave/cli.py tests/test_cli.py
git commit -m "feat: add poll + backfill CLI entrypoints"
```

---

## Phase 7 — Docs

### Task 21: Backend README + env reference

**Files:**
- Create: `backend/README.md`

- [ ] **Step 1: Write the README**

Document: local dev (uv sync, docker-compose, alembic upgrade, uvicorn), the full
`TIDALWAVE_*` env var reference (database_url, lastfm_api_key/secret, public_base_url,
registration_mode/allowlist, session_secret), how the Last.fm connect flow works, and how
to run the poller (`tidalwave-poll`, intended as a cron/Kubernetes CronJob ~every 5 min)
and a backfill (`tidalwave-backfill <lastfm-username>`).

- [ ] **Step 2: Commit**

```bash
cd backend && git add README.md
git commit -m "docs: add backend README + env reference"
```

---

## Self-Review Notes (for the implementer)

- **Spec coverage:** Connect-flow (T17), create-or-login + admin (T9), allowlist (T8),
  per-user dedup ingest (T11–T12), backfill (T13), poller (T14), stats incl. listening
  clock (T15), gated routes (T18), shares (T19), config incl. REGISTRATION_MODE (T2).
  Frontend dashboards and Helm/Flux deployment are in-scope for the product but
  out-of-scope for *this backend plan* — they are intentionally deferred to the follow-up
  plan.
- **DB tests need Postgres:** the dedup upsert and `extract('hour', ...)` use Postgres
  features; `docker-compose up -d` must be running. Do not switch tests to SQLite.
- **Cross-connection visibility:** route tests that seed via `db_session` must `commit()`
  before the ASGI request, because the app uses its own connection. This is called out in
  Task 18.
