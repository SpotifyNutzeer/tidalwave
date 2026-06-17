# tidalwave — backend

tidalwave is a self-hosted, multi-user listening tracker for Tidal. Because Tidal does not expose a listening-history API, users scrobble their Tidal plays to Last.fm (via the Tidal app or a scrobbler) and tidalwave pulls that history through the Last.fm `user.getRecentTracks` API. The backend is a FastAPI service backed by PostgreSQL; it handles Last.fm OAuth-style authentication, per-user scrobble ingestion, stats aggregation, and shareable read-only links.

---

## Local development

**Prerequisites:** [uv](https://docs.astral.sh/uv/) and a running PostgreSQL instance.

The easiest way to get Postgres is via Docker Compose:

```bash
docker-compose up -d        # starts postgres:16 on localhost:5432
```

Then install dependencies, run migrations, and start the dev server:

```bash
uv sync
uv run alembic upgrade head
uv run uvicorn tidalwave.main:app --reload --port 8080
```

The API is now available at `http://localhost:8080`.

---

## Environment variables

All settings are read from environment variables prefixed with `TIDALWAVE_` (or from a `.env` file in the working directory).

| Variable | Default | Description |
|---|---|---|
| `TIDALWAVE_DATABASE_URL` | `postgresql+asyncpg://tidalwave:tidalwave@localhost:5432/tidalwave` | Async SQLAlchemy connection URL for PostgreSQL. |
| `TIDALWAVE_LASTFM_API_KEY` | *(empty)* | Last.fm API key. Obtain one at https://www.last.fm/api/account/create. |
| `TIDALWAVE_LASTFM_API_SECRET` | *(empty)* | Last.fm API secret corresponding to the key above. |
| `TIDALWAVE_PUBLIC_BASE_URL` | `http://localhost:8080` | Public base URL of this service. Used to build the `cb=` callback parameter sent to Last.fm during auth. Must be reachable by the browser completing the OAuth flow. |
| `TIDALWAVE_REGISTRATION_MODE` | `allowlist` | Controls who may connect a Last.fm account. `open` allows anyone; `allowlist` restricts to the usernames listed in `TIDALWAVE_REGISTRATION_ALLOWLIST`. |
| `TIDALWAVE_REGISTRATION_ALLOWLIST` | *(empty)* | Comma-separated list of Last.fm usernames permitted to register when `REGISTRATION_MODE=allowlist`. Example: `alice,bob`. |
| `TIDALWAVE_SESSION_SECRET` | `dev-insecure-change-me` | Secret used to sign the session cookie with itsdangerous. **Must be set to a strong random value in production.** |
| `TIDALWAVE_LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |

---

## Last.fm connect flow

1. Register a Last.fm API account at https://www.last.fm/api/account/create to obtain an API key and secret. Set `TIDALWAVE_LASTFM_API_KEY` and `TIDALWAVE_LASTFM_API_SECRET`.
2. A user visits `GET /auth/login`. The server redirects the browser to Last.fm's authorization page.
3. Last.fm redirects back to `GET /auth/callback?token=<token>`. The server exchanges the one-time token for a permanent session key, then creates or logs in the user via `upsert_user_from_session`.
4. The first user to connect automatically becomes admin. Subsequent registrations are gated by `TIDALWAVE_REGISTRATION_MODE`; a 403 is returned if the Last.fm username is not on the allowlist when mode is `allowlist`.
5. On success the server sets an `httponly` session cookie and redirects to `/`.
6. `POST /auth/logout` clears the cookie.

---

## Endpoints

### Health

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Returns `{"status": "ok"}`. |

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/auth/login` | None | Redirects to Last.fm authorization page. |
| `GET` | `/auth/callback` | None | Receives Last.fm token, creates/logs in user, sets session cookie. |
| `POST` | `/auth/logout` | None | Clears session cookie. |

### Stats (session-gated — requires valid session cookie)

| Method | Path | Query params | Description |
|---|---|---|---|
| `GET` | `/stats/top-artists` | `limit` (default 20) | Top artists by listen count for the authenticated user. |
| `GET` | `/stats/top-tracks` | `limit` (default 20) | Top tracks by listen count. |
| `GET` | `/stats/top-albums` | `limit` (default 20) | Top albums by listen count. |
| `GET` | `/stats/clock` | — | 24-element array of listen counts by hour of day. |
| `GET` | `/stats/recent` | `limit` (default 50) | Most recent listens. |
| `GET` | `/stats/summary` | — | `{"total_listens": N}`. |

### Shares (session-gated)

| Method | Path | Description |
|---|---|---|
| `POST` | `/shares` | Creates a new share token for the authenticated user. Returns `{"share_token": "..."}`. |
| `DELETE` | `/shares/{token}` | Revokes a share token owned by the authenticated user. |

### Public shared views (no auth required)

| Method | Path | Description |
|---|---|---|
| `GET` | `/shared/{token}/top-artists` | Top artists for the share's owner (read-only, no login required). |
| `GET` | `/shared/{token}/summary` | Total listens for the share's owner. |

---

## Running the poller and backfill

These are console scripts installed by `uv sync` (see `[project.scripts]` in `pyproject.toml`).

**One-pass poll** — fetches new scrobbles for every connected user since their last sync:

```bash
tidalwave-poll
```

This is intended to be run on a schedule, e.g. every 5 minutes via cron or a Kubernetes CronJob.

**Full-history backfill** — imports a user's entire Last.fm history (may take a while for accounts with many scrobbles):

```bash
tidalwave-backfill <lastfm-username>
```

Both commands read configuration from the same `TIDALWAVE_*` environment variables as the server.

---

## Tests

Tests require a running PostgreSQL instance. By default the test suite connects to the same URL as the application default (`postgresql+asyncpg://tidalwave:tidalwave@localhost:5432/tidalwave`). Override with:

```bash
export TIDALWAVE_TEST_DATABASE_URL=postgresql+asyncpg://...
```

Run the suite:

```bash
uv run pytest
```
