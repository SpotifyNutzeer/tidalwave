# Poll Last.fm immediately on connect — Design

## Problem

After a user connects their Last.fm account, their listening data only appears
after the next poller CronJob run (up to 5 minutes later). The first visit to the
dashboard is therefore empty. We want a successful connect to trigger an immediate
ingest of the user's recent tracks.

## Decisions

- **Trigger:** on **every** successful connect (first connect *and* reconnect),
  not only the first one.
- **Execution:** in the **background** (FastAPI `BackgroundTasks`). The login
  redirect returns immediately; the ingest runs afterwards. A failed ingest never
  affects the login response.

## Architecture

Three small, isolated changes. No new infrastructure, no job queue.

### 1. `ingest/poller.py` — extract per-user logic (refactor)

`poll_all_users` currently inlines the per-user "ingest + auth-error handling"
inside its loop. Extract it into a reusable helper:

```python
async def ingest_one_user(
    session: AsyncSession, client: RecentTracksSource, user: User
) -> int | str:
    """Ingest one user. Returns inserted count, or "disconnected"/"error".
    Auth errors (codes 4/9) flip user.disconnected; transient errors are logged."""
```

`poll_all_users` calls `ingest_one_user` in its loop and assembles the report.
Behaviour is unchanged — this only removes duplication so the trigger can reuse
the exact same error/disconnect semantics.

### 2. `ingest/poller.py` — single-user, resource-managed entrypoint (new)

```python
async def ingest_user_now(
    session_factory: async_sessionmaker[AsyncSession],
    client: RecentTracksSource,
    user_id: int,
) -> None:
    """Background-task entrypoint: open a fresh session, re-load the user by id,
    ingest, commit. Never raises — logs and returns."""
```

- Opens its **own** session from the factory (the request session is closed by
  the time the task runs).
- Re-loads the `User` by id (the ORM object from the request session must not be
  reused across sessions).
- Returns quietly if the user no longer exists.
- Delegates to `ingest_one_user`, then commits.
- Wraps everything so no exception escapes (the response is already sent).

### 3. `routes/auth.py` — schedule the task

The `callback` handler gains `background: BackgroundTasks` and `request: Request`.
After a successful `upsert_user_from_session`:

```python
background.add_task(
    ingest_user_now,
    request.app.state.session_factory,
    client,            # the already-injected get_lastfm_client
    user.id,
)
```

- `client` (from `get_lastfm_client`) wraps `app.state.http`, which is app-scoped
  and outlives the request → valid inside the background task.
- Injecting `BackgroundTasks` attaches the task to the returned `RedirectResponse`
  automatically; FastAPI runs it after the response is sent.

## Data flow

1. `/auth/callback` exchanges the token, upserts the user (committed when the
   request session finalizes).
2. The redirect to `/` is returned immediately.
3. After the response, `ingest_user_now` runs: new session → load user → for a
   brand-new user (no sync state) `ingest_user` fetches the full history; for an
   existing user it fetches incrementally from the sync floor → `upsert_listens`.
4. Concurrency with the 5-minute cron is safe: ingestion is idempotent via the
   dedup constraint and the sync-state floor.

## Error handling

Reuses the poller's semantics via `ingest_one_user`:
- Last.fm auth errors (codes 4/9) → `user.disconnected = True`.
- Transient errors → logged, no state change.
- `ingest_user_now` additionally guarantees no exception propagates out of the
  background task.

The login flow is never blocked or failed by ingest problems.

## Testing

- **Refactor safety:** existing `poll_all_users` tests stay green; optionally add a
  direct unit test for `ingest_one_user`.
- **Trigger integration test:** call `/auth/callback` with a stubbed token exchange
  and an overridden `get_lastfm_client` returning canned recent tracks. The
  `TestClient` runs background tasks after the response, so assert the user's
  listens are persisted afterwards — for both a first connect and a repeat connect.

## Out of scope (YAGNI)

- No separate full-backfill path (first-time `ingest_user` already imports
  everything).
- No job queue, no progress/status feedback in the UI.
