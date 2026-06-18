# Poll Last.fm immediately on connect — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trigger an immediate background ingest of a user's Last.fm recent tracks on every successful connect, so the dashboard isn't empty until the next 5-minute cron run.

**Architecture:** Extract the poller's per-user "ingest + auth-error handling" into a reusable `ingest_one_user`. Add a resource-managed single-user entrypoint `ingest_user_now` that opens its own session and commits. Schedule it from the `/auth/callback` handler via FastAPI `BackgroundTasks`, so the login redirect returns immediately.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, asyncpg, pytest / pytest-asyncio, uv.

## Global Constraints

- Run all commands from `backend/` (e.g. `cd backend`).
- Use `uv run` for Python/pytest (e.g. `uv run pytest`, `uv run ruff check src tests`, `uv run mypy src`).
- Async tests use the existing `db_session` / `api` fixtures in `tests/conftest.py`; tests are `async def` (pytest-asyncio is configured).
- Ingestion is idempotent (dedup constraint + sync-state floor) — never special-case "already ingested".
- Match existing style: `from __future__ import annotations`, module-level `log = logging.getLogger(__name__)`.

---

### Task 1: Extract `ingest_one_user` from the poller

**Files:**
- Modify: `backend/src/tidalwave/ingest/poller.py`
- Test: `backend/tests/ingest/test_poller.py` (existing tests must stay green; add one focused test)

**Interfaces:**
- Produces: `async def ingest_one_user(session: AsyncSession, client: RecentTracksSource, user: User) -> int | str` — ingests one user; returns the inserted count, or `"disconnected"` (auth error codes 4/9, sets `user.disconnected = True`) or `"error"` (transient). Does NOT commit (caller commits/flushes).
- Consumes: existing `ingest_user` (from `tidalwave.ingest.service`), `_AUTH_ERROR_CODES`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/ingest/test_poller.py` (the `FakeClient`, `_page`, and imports already exist in this file):

```python
async def test_ingest_one_user_disconnects_on_auth_error(db_session):
    from tidalwave.ingest.poller import ingest_one_user

    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    await db_session.flush()

    client = FakeClient({}, errors={"alice": LastfmError(9, "Invalid session key")})
    result = await ingest_one_user(db_session, client, user)

    assert result == "disconnected"
    assert user.disconnected is True


async def test_ingest_one_user_returns_inserted_count(db_session):
    from tidalwave.ingest.poller import ingest_one_user

    user = await upsert_user_from_session(db_session, "bob", "sk", mode="open", allowlist=[])
    await db_session.flush()

    result = await ingest_one_user(db_session, FakeClient({"bob": _page(1000)}), user)
    assert result == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/ingest/test_poller.py::test_ingest_one_user_disconnects_on_auth_error -v`
Expected: FAIL — `ImportError: cannot import name 'ingest_one_user'`

- [ ] **Step 3: Refactor `poller.py` to add `ingest_one_user` and call it from the loop**

Replace the body of `poll_all_users` and add the helper. The full file becomes:

```python
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
```

- [ ] **Step 4: Run the poller tests (new + existing) to verify they pass**

Run: `cd backend && uv run pytest tests/ingest/test_poller.py -v`
Expected: PASS (the two new tests plus the pre-existing `test_poll_*` tests).

- [ ] **Step 5: Lint, type-check, commit**

```bash
cd backend && uv run ruff check src tests && uv run mypy src
git add src/tidalwave/ingest/poller.py tests/ingest/test_poller.py
git commit -m "refactor(ingest): extract ingest_one_user from poll_all_users"
```

---

### Task 2: Add the `ingest_user_now` background entrypoint

**Files:**
- Modify: `backend/src/tidalwave/ingest/poller.py`
- Test: `backend/tests/ingest/test_ingest_now.py` (create)

**Interfaces:**
- Consumes: `ingest_one_user` (Task 1), `session_scope` (from `tidalwave.db`).
- Produces: `async def ingest_user_now(session_factory: async_sessionmaker[AsyncSession], client: RecentTracksSource, user_id: int) -> None` — opens its own session, re-loads the user by id, ingests, commits. Never raises (logs unexpected errors). No-ops if the user is gone.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/ingest/test_ingest_now.py`:

```python
from datetime import UTC, datetime

import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from tidalwave.auth.service import upsert_user_from_session
from tidalwave.ingest.poller import ingest_user_now
from tidalwave.lastfm.client import LastfmError, RecentTracksPage
from tidalwave.models.db import Listen
from tidalwave.models.domain import Scrobble


class FakeClient:
    def __init__(self, by_user, errors=None):
        self.by_user = by_user
        self.errors: dict[str, LastfmError] = errors or {}

    async def get_recent_tracks(self, username, *, from_ts=None, page=1, limit=200, session_key=None):
        if username in self.errors:
            raise self.errors[username]
        return self.by_user[username]


def _page(ts):
    return RecentTracksPage(
        (Scrobble(artist="A", track_title="t", album=None,
                  played_at=datetime.fromtimestamp(ts, tz=UTC)),),
        page=1, total_pages=1,
    )


@pytest_asyncio.fixture
async def committing_factory(_engine):
    # A factory whose sessions share one connection via SAVEPOINTs, so the
    # real commit() inside ingest_user_now is visible to later reads in the
    # test yet fully rolled back at teardown.
    connection = await _engine.connect()
    trans = await connection.begin()
    factory = async_sessionmaker(
        bind=connection, expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield factory
    finally:
        await trans.rollback()
        await connection.close()


async def test_ingest_user_now_stores_listens(committing_factory):
    async with committing_factory() as s:
        user = await upsert_user_from_session(s, "alice", "sk", mode="open", allowlist=[])
        await s.commit()
        uid = user.id

    await ingest_user_now(committing_factory, FakeClient({"alice": _page(1000)}), uid)

    async with committing_factory() as s:
        listens = (await s.execute(select(Listen).where(Listen.user_id == uid))).scalars().all()
    assert len(listens) == 1


async def test_ingest_user_now_noops_for_missing_user(committing_factory):
    # Must not raise when the user id does not exist.
    await ingest_user_now(committing_factory, FakeClient({}), 999999)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/ingest/test_ingest_now.py -v`
Expected: FAIL — `ImportError: cannot import name 'ingest_user_now'`

- [ ] **Step 3: Implement `ingest_user_now` in `poller.py`**

Add these imports at the top of `backend/src/tidalwave/ingest/poller.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tidalwave.db import session_scope
```

(Replace the existing `from sqlalchemy.ext.asyncio import AsyncSession` line with the combined import above.)

Append to the end of `backend/src/tidalwave/ingest/poller.py`:

```python
async def ingest_user_now(
    session_factory: async_sessionmaker[AsyncSession],
    client: RecentTracksSource,
    user_id: int,
) -> None:
    """Background-task entrypoint: ingest a single user right after they connect.

    Opens its own session (the request session is closed by now), re-loads the
    user by id, ingests, and commits. Never raises — the HTTP response is already
    sent, so failures are only logged.
    """
    try:
        async with session_scope(session_factory) as session:
            user = await session.get(User, user_id)
            if user is None:
                return
            await ingest_one_user(session, client, user)
            await session.commit()
    except Exception:
        log.exception("immediate ingest failed for user_id=%s", user_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/ingest/test_ingest_now.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Lint, type-check, commit**

```bash
cd backend && uv run ruff check src tests && uv run mypy src
git add src/tidalwave/ingest/poller.py tests/ingest/test_ingest_now.py
git commit -m "feat(ingest): add ingest_user_now background entrypoint"
```

---

### Task 3: Trigger the ingest from the auth callback

**Files:**
- Modify: `backend/src/tidalwave/routes/auth.py`
- Test: `backend/tests/routes/test_auth_routes.py` (add one test)

**Interfaces:**
- Consumes: `ingest_user_now` (Task 2), `request.app.state.session_factory`, the `get_lastfm_client` result, and `user.id` from `upsert_user_from_session`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/routes/test_auth_routes.py`:

```python
async def test_callback_schedules_immediate_ingest(api, monkeypatch):
    client, app = api
    from tidalwave.deps import get_lastfm_client
    from tidalwave.routes import auth as auth_module

    class FakeLastfm:
        async def get_session(self, token):
            return ("alice", "SESS")

    fake = FakeLastfm()
    app.dependency_overrides[get_lastfm_client] = lambda: fake

    calls = []

    async def spy(session_factory, lastfm_client, user_id):
        calls.append((session_factory, lastfm_client, user_id))

    monkeypatch.setattr(auth_module, "ingest_user_now", spy)

    resp = await client.get("/auth/callback?token=TOK", follow_redirects=False)
    assert resp.status_code == 307

    # FastAPI runs background tasks after the response is sent.
    assert len(calls) == 1
    session_factory, lastfm_client, user_id = calls[0]
    assert session_factory is app.state.session_factory
    assert lastfm_client is fake
    assert isinstance(user_id, int)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_auth_routes.py::test_callback_schedules_immediate_ingest -v`
Expected: FAIL — `AttributeError: <module 'tidalwave.routes.auth'> has no attribute 'ingest_user_now'` (the name isn't imported/used yet).

- [ ] **Step 3: Wire the background task into the callback**

In `backend/src/tidalwave/routes/auth.py`:

Add `BackgroundTasks` and `Request` to the fastapi import, and import `ingest_user_now`:

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
```

```python
from tidalwave.ingest.poller import ingest_user_now
```

Change the `callback` signature to inject `background` and `request`:

```python
@router.get("/callback")
async def callback(
    token: str,
    background: BackgroundTasks,
    request: Request,
    client: LastfmClient = Depends(get_lastfm_client),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
```

Immediately after the `upsert_user_from_session` try/except block (after `user` is assigned, before building the cookie), add:

```python
    background.add_task(
        ingest_user_now, request.app.state.session_factory, client, user.id
    )
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && uv run pytest tests/routes/test_auth_routes.py -v`
Expected: PASS (the new test plus the existing `test_callback_*` / `test_login_*` / `test_me_*` tests).

- [ ] **Step 5: Full suite, lint, type-check, commit**

```bash
cd backend && uv run pytest -q && uv run ruff check src tests && uv run mypy src
git add src/tidalwave/routes/auth.py tests/routes/test_auth_routes.py
git commit -m "feat(auth): poll Last.fm immediately on connect"
```

---

## Notes for the reviewer / merge

- This is backend-only; no schema change, no migration, no chart/values change. It ships in the next image build/release (a `0.1.x` bump) — not part of this plan.
- The `committing_factory` test fixture (Task 2) uses `join_transaction_mode="create_savepoint"` so a real `commit()` stays isolated; do not "simplify" it to the plain `db_session` fixture, which would make the committed rows leak or be invisible.
