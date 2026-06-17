# tidalwave Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the SvelteKit dashboard frontend for tidalwave — a gated multi-user Last.fm listening dashboard with charts, plus the two small backend endpoints it needs.

**Architecture:** SvelteKit (`adapter-static`, SPA fallback) + Svelte 5 + TypeScript, mirroring the sibling `linkhop` frontend's conventions (typed API client generated from the backend OpenAPI schema, Catppuccin theme tokens, vitest component tests, Playwright E2E). The static SPA talks to the FastAPI backend same-origin; cookies (`credentials: "include"`) carry the session. Charts use **LayerChart** (Svelte-native). Two new backend endpoints are added first: `/auth/me` (so the SPA can tell logged-in from logged-out) and the remaining public `/shared/{token}/*` stat endpoints (so a shared link renders the full read-only dashboard, not just two cards).

**Tech Stack:** SvelteKit 2, Svelte 5, TypeScript, Vite, `@sveltejs/adapter-static`, LayerChart, vitest + @testing-library/svelte + jsdom, Playwright, openapi-typescript. Backend additions: FastAPI (Python 3.12, existing `tidalwave` package).

## Global Constraints

- Node **>= 22.12**, package manager **pnpm** (mirror linkhop's `packageManager` pin). The execution environment has only Node 20 + npm — the FIRST frontend task must bootstrap Node 22 + pnpm (e.g. via `corepack`/`nvm`/`fnm`); document what was used.
- Backend Python work uses `uv` (already installed); run backend tests with `uv run pytest` against the running local Postgres (`postgresql+asyncpg://tidalwave:tidalwave@localhost:5432/tidalwave`).
- The backend API is served at root paths: `/health`, `/auth/*`, `/stats/*`, `/shares`, `/shared/{token}/*` (NOT under `/api`). The frontend dev proxy and prod nginx forward exactly these prefixes to the backend.
- All authenticated API calls must send cookies: `fetch(..., { credentials: "include" })`.
- Frontend lives in `/root/git/tidalwave/frontend/`. Backend lives in `/root/git/tidalwave/backend/`.
- Match linkhop's Catppuccin Mocha/Latte theming approach (`src/lib/theme/tokens.css` + a `theme` store + `ThemeToggle`). You may read `linkhop/frontend/src/lib/theme/tokens.css`, `.../stores/theme.ts`, and `.../components/ThemeToggle.svelte` as the reference to copy/adapt.

---

## File Structure

```
backend/  (additions only)
  src/tidalwave/routes/auth.py      # + GET /auth/me
  src/tidalwave/routes/share.py     # + remaining /shared/{token}/* endpoints
  tests/routes/test_auth_routes.py  # + /auth/me tests
  tests/routes/test_share_routes.py # + shared-endpoint tests

frontend/
  package.json, svelte.config.js, vite.config.ts, tsconfig.json, playwright.config.ts
  src/app.html, src/app.d.ts, src/test/setup.ts
  src/lib/theme/tokens.css
  src/lib/api/schema.d.ts            # generated from backend openapi.json
  src/lib/api/client.ts              # typed fetch wrapper (credentials: include)
  src/lib/stores/theme.ts
  src/lib/stores/auth.ts             # current user / login state
  src/lib/format.ts                  # small pure formatting helpers (weekday names, etc.)
  src/lib/components/Header.svelte
  src/lib/components/ThemeToggle.svelte
  src/lib/components/ConnectButton.svelte
  src/lib/components/SummaryCard.svelte
  src/lib/components/TopList.svelte
  src/lib/components/ListeningClock.svelte
  src/lib/components/WeekdayChart.svelte
  src/lib/components/HistoryChart.svelte
  src/lib/components/RecentList.svelte
  src/lib/components/ShareManager.svelte
  src/lib/components/Dashboard.svelte
  src/routes/+layout.svelte, +layout.ts
  src/routes/+page.svelte            # dashboard when logged in, ConnectButton landing otherwise
  src/routes/s/[token]/+page.svelte, +page.ts   # public shared page (route /s/{token}; backend API stays /shared/{token}/*)
  nginx.conf
```

> **Routing note:** the public shared *page* lives at `/s/{token}` (frontend), while the
> public shared *API* lives at `/shared/{token}/*` (backend). They use distinct path
> prefixes on purpose so the production Ingress can route `/shared` → backend and `/s` (under
> `/`) → frontend without collision. See the deployment plan.
```

---

## Phase 0 — Backend support endpoints

### Task 1: `GET /auth/me`

**Files:**
- Modify: `backend/src/tidalwave/routes/auth.py`
- Test: `backend/tests/routes/test_auth_routes.py`

**Interfaces:**
- Consumes: `current_user` dependency (`tidalwave.auth.session.current_user`), `User` model (fields `id`, `lastfm_username`, `is_admin`).
- Produces: `GET /auth/me` → `200 {"username": str, "is_admin": bool}` when authenticated; `401` otherwise (via `current_user`).

- [ ] **Step 1: Write the failing test** (append to `backend/tests/routes/test_auth_routes.py`)

```python
async def test_me_returns_401_when_anonymous(api):
    client, app = api
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_returns_current_user(api, db_session):
    from tidalwave.auth.service import upsert_user_from_session
    from tidalwave.auth.session import COOKIE_NAME, SessionCodec

    client, app = api
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    cookie = SessionCodec("test-secret").encode(user.id)
    resp = await client.get("/auth/me", headers={"Cookie": f"{COOKIE_NAME}={cookie}"})
    assert resp.status_code == 200
    assert resp.json() == {"username": "alice", "is_admin": True}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_auth_routes.py -k me -v`
Expected: FAIL — 404 (no `/auth/me` route).

- [ ] **Step 3: Implement** — add to `backend/src/tidalwave/routes/auth.py`

Add these imports if not already present: `from fastapi import Depends` (already imported) and `from tidalwave.auth.session import current_user`, `from tidalwave.models.db import User`. Then add the route:

```python
@router.get("/me")
async def me(user: User = Depends(current_user)) -> dict:
    return {"username": user.lastfm_username, "is_admin": user.is_admin}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/routes/test_auth_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/backend
git add src/tidalwave/routes/auth.py tests/routes/test_auth_routes.py
git commit -m "feat: add /auth/me endpoint"
```

---

### Task 2: Complete the public shared stat endpoints

**Files:**
- Modify: `backend/src/tidalwave/routes/share.py`
- Test: `backend/tests/routes/test_share_routes.py`

**Interfaces:**
- Consumes: `_resolve_share(session, token) -> Share` (already in `share.py`), `tidalwave.stats.queries` functions: `top_tracks`, `top_albums`, `listening_clock`, `listening_weekday`, `listens_over_time`, `recent_listens` (all accept `session, user_id, *, ...`; the top/clock/weekday/history ones accept `since`/`until`; `listens_over_time` also `bucket`; `recent_listens` accepts `limit` only).
- Produces: public GET endpoints (no auth), honoring `share.range_from`/`range_to` where the query supports it:
  - `GET /shared/{token}/top-tracks?limit=` → `list[dict]`
  - `GET /shared/{token}/top-albums?limit=` → `list[dict]`
  - `GET /shared/{token}/clock` → `list[int]`
  - `GET /shared/{token}/weekday` → `list[int]`
  - `GET /shared/{token}/history?bucket=day` → `list[dict]`
  - `GET /shared/{token}/recent?limit=` → `list[dict]`

- [ ] **Step 1: Write the failing test** (append to `backend/tests/routes/test_share_routes.py`)

```python
async def test_shared_full_dashboard_endpoints(api, db_session):
    from datetime import UTC, datetime
    from tidalwave.auth.service import upsert_user_from_session
    from tidalwave.auth.session import COOKIE_NAME, SessionCodec
    from tidalwave.ingest.repository import upsert_listens
    from tidalwave.models.domain import Scrobble

    client, app = api
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    await upsert_listens(db_session, user.id, [
        Scrobble(artist="Kavinsky", track_title="Nightcall", album="OutRun",
                 played_at=datetime(2024, 6, 17, 12, tzinfo=UTC)),
    ])
    cookie = SessionCodec("test-secret").encode(user.id)
    token = (await client.post("/shares", headers={"Cookie": f"{COOKIE_NAME}={cookie}"})).json()["share_token"]

    assert (await client.get(f"/shared/{token}/top-tracks")).json()[0]["track"] == "Nightcall"
    assert (await client.get(f"/shared/{token}/top-albums")).json()[0]["album"] == "OutRun"
    assert len(await (await client.get(f"/shared/{token}/clock")).aread()) > 0
    assert (await client.get(f"/shared/{token}/clock")).json()[12] == 1   # hour 12 UTC
    assert (await client.get(f"/shared/{token}/weekday")).json()[0] == 1  # Monday
    assert (await client.get(f"/shared/{token}/history?bucket=day")).json()[0]["count"] == 1
    assert (await client.get(f"/shared/{token}/recent")).json()[0]["track"] == "Nightcall"


async def test_shared_endpoints_404_when_revoked(api, db_session):
    from tidalwave.auth.service import upsert_user_from_session
    from tidalwave.auth.session import COOKIE_NAME, SessionCodec

    client, app = api
    user = await upsert_user_from_session(db_session, "alice", "sk", mode="open", allowlist=[])
    auth = {"Cookie": f"{COOKIE_NAME}={SessionCodec('test-secret').encode(user.id)}"}
    token = (await client.post("/shares", headers=auth)).json()["share_token"]
    await client.delete(f"/shares/{token}", headers=auth)
    assert (await client.get(f"/shared/{token}/top-tracks")).status_code == 404
    assert (await client.get(f"/shared/{token}/clock")).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/routes/test_share_routes.py -k "full_dashboard or revoked" -v`
Expected: FAIL — 404 on the new paths (routes don't exist).

- [ ] **Step 3: Implement** — add to `backend/src/tidalwave/routes/share.py`

The file already has `_resolve_share`, `router`, and `from tidalwave.stats import queries`. Add the following endpoints (mirror the existing `shared_top_artists`/`shared_summary` style — resolve the share, then call the query with the share owner's `user_id` and the share's range bounds where supported):

```python
@router.get("/shared/{token}/top-tracks")
async def shared_top_tracks(token: str, limit: int = 20,
                            session: AsyncSession = Depends(get_session)) -> list[dict]:
    share = await _resolve_share(session, token)
    return await queries.top_tracks(session, share.user_id, limit=limit,
                                    since=share.range_from, until=share.range_to)


@router.get("/shared/{token}/top-albums")
async def shared_top_albums(token: str, limit: int = 20,
                            session: AsyncSession = Depends(get_session)) -> list[dict]:
    share = await _resolve_share(session, token)
    return await queries.top_albums(session, share.user_id, limit=limit,
                                    since=share.range_from, until=share.range_to)


@router.get("/shared/{token}/clock")
async def shared_clock(token: str, session: AsyncSession = Depends(get_session)) -> list[int]:
    share = await _resolve_share(session, token)
    return await queries.listening_clock(session, share.user_id,
                                         since=share.range_from, until=share.range_to)


@router.get("/shared/{token}/weekday")
async def shared_weekday(token: str, session: AsyncSession = Depends(get_session)) -> list[int]:
    share = await _resolve_share(session, token)
    return await queries.listening_weekday(session, share.user_id,
                                           since=share.range_from, until=share.range_to)


@router.get("/shared/{token}/history")
async def shared_history(token: str, bucket: Literal["day", "week", "month"] = "day",
                         session: AsyncSession = Depends(get_session)) -> list[dict]:
    share = await _resolve_share(session, token)
    return await queries.listens_over_time(session, share.user_id, bucket=bucket,
                                           since=share.range_from, until=share.range_to)


@router.get("/shared/{token}/recent")
async def shared_recent(token: str, limit: int = 50,
                        session: AsyncSession = Depends(get_session)) -> list[dict]:
    share = await _resolve_share(session, token)
    return await queries.recent_listens(session, share.user_id, limit=limit)
```

Add `from typing import Literal` at the top of `share.py` if not already imported.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/routes/test_share_routes.py -v && uv run ruff check . && uv run mypy src`
Expected: PASS, zero ruff errors, mypy clean.

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/backend
git add src/tidalwave/routes/share.py tests/routes/test_share_routes.py
git commit -m "feat: expose full read-only dashboard on share links"
```

---

## Phase 1 — Frontend scaffold

### Task 3: Frontend scaffold + smoke test

**Files:**
- Create: `frontend/package.json`, `frontend/svelte.config.js`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/src/app.html`, `frontend/src/app.d.ts`, `frontend/src/test/setup.ts`, `frontend/src/routes/+page.svelte`, `frontend/.gitignore`
- Test: `frontend/src/routes/page.smoke.test.ts`

**Interfaces:**
- Produces: a runnable SvelteKit dev server (`pnpm dev` on :5173, `/api`-style proxying configured per Global Constraints) and a passing vitest setup.

- [ ] **Step 1: Bootstrap Node 22 + pnpm**

The environment has Node 20 + npm only. Install Node 22 and enable pnpm. Try in order: `corepack enable && corepack prepare pnpm@10 --activate`; if Node is still 20 and corepack pnpm needs Node 22, install Node 22 via your available manager (e.g. `nvm install 22 && nvm use 22`, or download the official tarball). Verify `node --version` ≥ 22.12 and `pnpm --version`. Report exactly what you used. If you cannot get Node ≥ 22.12, STOP and report BLOCKED.

- [ ] **Step 2: Create the project config files**

```json
// frontend/package.json
{
  "name": "tidalwave-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "engines": { "node": ">=22.12" },
  "packageManager": "pnpm@10.33.0",
  "scripts": {
    "prepare": "svelte-kit sync",
    "gen:api": "openapi-typescript ../backend/openapi.json -o src/lib/api/schema.d.ts",
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview",
    "check": "svelte-check --tsconfig ./tsconfig.json",
    "test": "vitest run",
    "test:e2e": "playwright test"
  },
  "devDependencies": {
    "@sveltejs/adapter-static": "^3.0.0",
    "@sveltejs/kit": "^2.60.1",
    "@sveltejs/vite-plugin-svelte": "^6.0.0",
    "@testing-library/jest-dom": "^6.4.0",
    "@testing-library/svelte": "^5.2.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/node": "^22.0.0",
    "jsdom": "^24.0.0",
    "openapi-typescript": "^7.13.0",
    "svelte": "^5.55.7",
    "svelte-check": "^4.0.0",
    "tslib": "^2.6.0",
    "typescript": "^5.4.0",
    "vite": "^7.3.0",
    "vitest": "^3.2.6"
  },
  "dependencies": {
    "layerchart": "^1.0.0"
  }
}
```

```javascript
// frontend/svelte.config.js
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',
      precompress: false,
      strict: true
    })
  }
};
```

```typescript
// frontend/vite.config.ts
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

// API paths served at root by the backend; proxy each prefix in dev.
const API_PREFIXES = ['/health', '/auth', '/stats', '/shares', '/shared'];

export default defineConfig({
  plugins: [sveltekit()],
  resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
  server: {
    port: 5173,
    proxy: Object.fromEntries(
      API_PREFIXES.map((p) => [p, 'http://127.0.0.1:8080'])
    )
  },
  test: {
    globals: true,
    environment: 'jsdom',
    environmentOptions: { jsdom: { url: 'http://localhost/' } },
    setupFiles: ['src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.ts']
  }
});
```

```json
// frontend/tsconfig.json
{
  "extends": "./.svelte-kit/tsconfig.json",
  "compilerOptions": {
    "allowJs": true,
    "checkJs": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "skipLibCheck": true,
    "sourceMap": true,
    "strict": true,
    "moduleResolution": "bundler"
  }
}
```

```html
<!-- frontend/src/app.html -->
<!doctype html>
<html lang="en" data-theme="mocha">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%sveltekit.assets%/favicon.png" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>tidalwave</title>
    %sveltekit.head%
  </head>
  <body data-sveltekit-preload-data="hover">
    <div style="display: contents">%sveltekit.body%</div>
  </body>
</html>
```

```typescript
// frontend/src/app.d.ts
declare global {
  namespace App {}
}
export {};
```

```typescript
// frontend/src/test/setup.ts
import '@testing-library/jest-dom/vitest';
```

```svelte
<!-- frontend/src/routes/+page.svelte -->
<h1>tidalwave</h1>
```

```
# frontend/.gitignore
node_modules/
/build
/.svelte-kit
/package
.env
.env.*
!.env.example
```

- [ ] **Step 3: Write the smoke test**

```typescript
// frontend/src/routes/page.smoke.test.ts
import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import Page from './+page.svelte';

describe('home page', () => {
  it('renders the app title', () => {
    render(Page);
    expect(screen.getByRole('heading', { name: 'tidalwave' })).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Install, sync, and run the smoke test**

Run:
```bash
cd /root/git/tidalwave/frontend
pnpm install
pnpm exec svelte-kit sync
pnpm test
```
Expected: 1 passing test. (`svelte-kit sync` must run before type-check/tests so `.svelte-kit/tsconfig.json` exists.)

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add -A
git commit -m "chore: scaffold tidalwave SvelteKit frontend"
```

---

### Task 4: Typed API client

**Files:**
- Create: `frontend/src/lib/api/client.ts`, `frontend/src/lib/api/schema.d.ts` (generated)
- Test: `frontend/src/lib/api/client.test.ts`
- Add (one-off): `backend/openapi.json` export

**Interfaces:**
- Produces a typed client object `api` with methods returning parsed JSON, all using `credentials: "include"`:
  - `api.me(): Promise<{ username: string; is_admin: boolean } | null>` — returns `null` on 401.
  - `api.summary(): Promise<{ total_listens: number }>`
  - `api.topArtists(limit?): Promise<{ artist: string; count: number }[]>`
  - `api.topTracks(limit?): Promise<{ track: string; count: number }[]>`
  - `api.topAlbums(limit?): Promise<{ album: string; count: number }[]>`
  - `api.clock(): Promise<number[]>`  (24 ints)
  - `api.weekday(): Promise<number[]>`  (7 ints)
  - `api.history(bucket?): Promise<{ period: string; count: number }[]>`
  - `api.recent(limit?): Promise<{ track: string; artist: string; album: string | null; played_at: string }[]>`
  - `api.createShare(): Promise<{ share_token: string }>`
  - `api.revokeShare(token): Promise<void>`
  - `api.loginUrl(): string` → `"/auth/login"`
  - shared (public): `api.shared.topArtists(token)`, `.topTracks(token)`, `.topAlbums(token)`, `.clock(token)`, `.weekday(token)`, `.history(token, bucket?)`, `.recent(token)`, `.summary(token)` — same return shapes; throw on 404.

- [ ] **Step 1: Export the backend OpenAPI schema and generate types**

Run:
```bash
cd /root/git/tidalwave/backend
uv run python -c "import json; from tidalwave.main import app; print(json.dumps(app.openapi()))" > openapi.json
cd /root/git/tidalwave/frontend
pnpm gen:api
```
This writes `frontend/src/lib/api/schema.d.ts`. (Commit both `backend/openapi.json` and the generated `schema.d.ts`.)

- [ ] **Step 2: Write the failing test**

```typescript
// frontend/src/lib/api/client.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { api } from './client';

const okJson = (body: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } }));

describe('api client', () => {
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it('me() returns the user and sends credentials', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson({ username: 'alice', is_admin: true }) as any);
    const me = await api.me();
    expect(me).toEqual({ username: 'alice', is_admin: true });
    expect(fetchMock).toHaveBeenCalledWith('/auth/me', expect.objectContaining({ credentials: 'include' }));
  });

  it('me() returns null on 401', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson({ detail: 'no' }, 401) as any);
    expect(await api.me()).toBeNull();
  });

  it('topArtists() passes the limit query param', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson([{ artist: 'A', count: 3 }]) as any);
    const rows = await api.topArtists(5);
    expect(rows[0]).toEqual({ artist: 'A', count: 3 });
    expect(fetchMock).toHaveBeenCalledWith('/stats/top-artists?limit=5', expect.objectContaining({ credentials: 'include' }));
  });

  it('createShare() posts and returns the token', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson({ share_token: 'TOK' }, 201) as any);
    expect(await api.createShare()).toEqual({ share_token: 'TOK' });
    expect(fetchMock).toHaveBeenCalledWith('/shares', expect.objectContaining({ method: 'POST', credentials: 'include' }));
  });

  it('shared.topArtists() throws on 404', async () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(okJson({ detail: 'gone' }, 404) as any);
    await expect(api.shared.topArtists('TOK')).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd frontend && pnpm test src/lib/api/client.test.ts`
Expected: FAIL — cannot import `./client`.

- [ ] **Step 4: Implement the client**

```typescript
// frontend/src/lib/api/client.ts
// Thin typed wrapper over fetch. All calls are same-origin and send the session cookie.

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path, { credentials: 'include' });
  if (!res.ok) throw new ApiError(res.status, path);
  return (await res.json()) as T;
}

export class ApiError extends Error {
  constructor(public status: number, public path: string) {
    super(`API ${status} for ${path}`);
  }
}

export interface UserInfo { username: string; is_admin: boolean; }
export interface ArtistCount { artist: string; count: number; }
export interface TrackCount { track: string; count: number; }
export interface AlbumCount { album: string; count: number; }
export interface HistoryPoint { period: string; count: number; }
export interface RecentItem { track: string; artist: string; album: string | null; played_at: string; }
export type Bucket = 'day' | 'week' | 'month';

const q = (limit?: number) => (limit == null ? '' : `?limit=${limit}`);

export const api = {
  loginUrl: () => '/auth/login',

  async me(): Promise<UserInfo | null> {
    const res = await fetch('/auth/me', { credentials: 'include' });
    if (res.status === 401) return null;
    if (!res.ok) throw new ApiError(res.status, '/auth/me');
    return (await res.json()) as UserInfo;
  },

  summary: () => get<{ total_listens: number }>('/stats/summary'),
  topArtists: (limit?: number) => get<ArtistCount[]>(`/stats/top-artists${q(limit)}`),
  topTracks: (limit?: number) => get<TrackCount[]>(`/stats/top-tracks${q(limit)}`),
  topAlbums: (limit?: number) => get<AlbumCount[]>(`/stats/top-albums${q(limit)}`),
  clock: () => get<number[]>('/stats/clock'),
  weekday: () => get<number[]>('/stats/weekday'),
  history: (bucket: Bucket = 'day') => get<HistoryPoint[]>(`/stats/history?bucket=${bucket}`),
  recent: (limit?: number) => get<RecentItem[]>(`/stats/recent${q(limit)}`),

  async createShare(): Promise<{ share_token: string }> {
    const res = await fetch('/shares', { method: 'POST', credentials: 'include' });
    if (!res.ok) throw new ApiError(res.status, '/shares');
    return (await res.json()) as { share_token: string };
  },
  async revokeShare(token: string): Promise<void> {
    const res = await fetch(`/shares/${token}`, { method: 'DELETE', credentials: 'include' });
    if (!res.ok) throw new ApiError(res.status, `/shares/${token}`);
  },

  shared: {
    summary: (t: string) => get<{ total_listens: number }>(`/shared/${t}/summary`),
    topArtists: (t: string) => get<ArtistCount[]>(`/shared/${t}/top-artists`),
    topTracks: (t: string) => get<TrackCount[]>(`/shared/${t}/top-tracks`),
    topAlbums: (t: string) => get<AlbumCount[]>(`/shared/${t}/top-albums`),
    clock: (t: string) => get<number[]>(`/shared/${t}/clock`),
    weekday: (t: string) => get<number[]>(`/shared/${t}/weekday`),
    history: (t: string, bucket: Bucket = 'day') => get<HistoryPoint[]>(`/shared/${t}/history?bucket=${bucket}`),
    recent: (t: string) => get<RecentItem[]>(`/shared/${t}/recent`)
  }
};
```

(The generated `schema.d.ts` documents the wire types; the hand-written interfaces above are the app-facing types. Keep them consistent with the backend responses.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && pnpm test src/lib/api/client.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /root/git/tidalwave
git add backend/openapi.json frontend/src/lib/api/
git commit -m "feat: add typed API client + generated schema"
```

---

## Phase 2 — Theming, layout, auth state

### Task 5: Theme tokens + store + ThemeToggle + Header

**Files:**
- Create: `frontend/src/lib/theme/tokens.css`, `frontend/src/lib/stores/theme.ts`, `frontend/src/lib/components/ThemeToggle.svelte`, `frontend/src/lib/components/Header.svelte`
- Create: `frontend/src/routes/+layout.svelte`
- Test: `frontend/src/lib/stores/theme.test.ts`

**Interfaces:**
- Produces: `theme` store (`'mocha' | 'latte'`) with `toggle()` and persistence to `localStorage` + `document.documentElement.dataset.theme`; `<ThemeToggle />`; `<Header />` showing the app name + theme toggle (+ a slot for actions).

- [ ] **Step 1: Reference linkhop, then write the failing test**

Read `linkhop/frontend/src/lib/stores/theme.ts` and `.../theme/tokens.css` as the reference for the Catppuccin variables and persistence pattern. Then:

```typescript
// frontend/src/lib/stores/theme.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { theme, toggleTheme } from './theme';

describe('theme store', () => {
  beforeEach(() => { localStorage.clear(); theme.set('mocha'); });

  it('toggles between mocha and latte', () => {
    toggleTheme();
    expect(get(theme)).toBe('latte');
    toggleTheme();
    expect(get(theme)).toBe('mocha');
  });

  it('persists the choice to localStorage', () => {
    toggleTheme();
    expect(localStorage.getItem('tw-theme')).toBe('latte');
  });

  it('reflects the choice on the document element', () => {
    toggleTheme();
    expect(document.documentElement.dataset.theme).toBe('latte');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test src/lib/stores/theme.test.ts`
Expected: FAIL — cannot import `./theme`.

- [ ] **Step 3: Implement**

```typescript
// frontend/src/lib/stores/theme.ts
import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export type Theme = 'mocha' | 'latte';
const KEY = 'tw-theme';

function initial(): Theme {
  if (!browser) return 'mocha';
  const saved = localStorage.getItem(KEY);
  return saved === 'latte' || saved === 'mocha' ? saved : 'mocha';
}

export const theme = writable<Theme>(initial());

theme.subscribe((value) => {
  if (!browser) return;
  localStorage.setItem(KEY, value);
  document.documentElement.dataset.theme = value;
});

export function toggleTheme(): void {
  theme.update((t) => (t === 'mocha' ? 'latte' : 'mocha'));
}
```

```css
/* frontend/src/lib/theme/tokens.css */
/* Catppuccin Mocha (default) + Latte. Mirror linkhop's palette. */
:root, [data-theme='mocha'] {
  --base: #1e1e2e; --mantle: #181825; --surface: #313244;
  --text: #cdd6f4; --subtext: #a6adc8; --mauve: #cba6f7; --blue: #89b4fa;
  --green: #a6e3a1; --peach: #fab387; --red: #f38ba8;
}
[data-theme='latte'] {
  --base: #eff1f5; --mantle: #e6e9ef; --surface: #ccd0da;
  --text: #4c4f69; --subtext: #6c6f85; --mauve: #8839ef; --blue: #1e66f5;
  --green: #40a02b; --peach: #fe640b; --red: #d20f39;
}
body { background: var(--base); color: var(--text); font-family: system-ui, sans-serif; margin: 0; }
```

```svelte
<!-- frontend/src/lib/components/ThemeToggle.svelte -->
<script lang="ts">
  import { theme, toggleTheme } from '$lib/stores/theme';
</script>

<button onclick={toggleTheme} aria-label="Toggle theme" title="Toggle theme">
  {$theme === 'mocha' ? '☾' : '☀'}
</button>

<style>
  button { background: var(--surface); color: var(--text); border: 0; border-radius: 6px; padding: 0.4rem 0.6rem; cursor: pointer; }
</style>
```

```svelte
<!-- frontend/src/lib/components/Header.svelte -->
<script lang="ts">
  import ThemeToggle from './ThemeToggle.svelte';
  let { children } = $props();
</script>

<header>
  <a class="brand" href="/">tidalwave</a>
  <div class="actions">
    {@render children?.()}
    <ThemeToggle />
  </div>
</header>

<style>
  header { display: flex; align-items: center; justify-content: space-between; padding: 1rem 1.5rem; background: var(--mantle); }
  .brand { color: var(--mauve); font-weight: 700; font-size: 1.25rem; text-decoration: none; }
  .actions { display: flex; gap: 0.75rem; align-items: center; }
</style>
```

```svelte
<!-- frontend/src/routes/+layout.svelte -->
<script lang="ts">
  import '$lib/theme/tokens.css';
  let { children } = $props();
</script>

{@render children?.()}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test src/lib/stores/theme.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add src/lib/theme src/lib/stores/theme.ts src/lib/components/ThemeToggle.svelte src/lib/components/Header.svelte src/routes/+layout.svelte
git commit -m "feat: add Catppuccin theme, toggle, header"
```

---

### Task 6: Auth store + ConnectButton + SPA mode

**Files:**
- Create: `frontend/src/lib/stores/auth.ts`, `frontend/src/lib/components/ConnectButton.svelte`
- Create: `frontend/src/routes/+layout.ts`
- Test: `frontend/src/lib/stores/auth.test.ts`

**Interfaces:**
- Consumes: `api.me()`, `api.loginUrl()`.
- Produces: `auth` store `{ user: UserInfo | null; loading: boolean }`; `loadMe(): Promise<void>` populates it; `<ConnectButton />` links to `api.loginUrl()`. `+layout.ts` sets `export const ssr = false;` (pure SPA — adapter-static fallback) and `export const prerender = false;`.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/lib/stores/auth.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { auth, loadMe } from './auth';
import { api } from '$lib/api/client';

describe('auth store', () => {
  beforeEach(() => { auth.set({ user: null, loading: false }); });

  it('loadMe populates the user when logged in', async () => {
    vi.spyOn(api, 'me').mockResolvedValue({ username: 'alice', is_admin: true });
    await loadMe();
    expect(get(auth).user).toEqual({ username: 'alice', is_admin: true });
    expect(get(auth).loading).toBe(false);
  });

  it('loadMe leaves user null when anonymous', async () => {
    vi.spyOn(api, 'me').mockResolvedValue(null);
    await loadMe();
    expect(get(auth).user).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test src/lib/stores/auth.test.ts`
Expected: FAIL — cannot import `./auth`.

- [ ] **Step 3: Implement**

```typescript
// frontend/src/lib/stores/auth.ts
import { writable } from 'svelte/store';
import { api, type UserInfo } from '$lib/api/client';

export interface AuthState { user: UserInfo | null; loading: boolean; }

export const auth = writable<AuthState>({ user: null, loading: true });

export async function loadMe(): Promise<void> {
  auth.update((s) => ({ ...s, loading: true }));
  const user = await api.me();
  auth.set({ user, loading: false });
}
```

```typescript
// frontend/src/routes/+layout.ts
export const ssr = false;
export const prerender = false;
```

```svelte
<!-- frontend/src/lib/components/ConnectButton.svelte -->
<script lang="ts">
  import { api } from '$lib/api/client';
</script>

<a class="connect" href={api.loginUrl()}>Connect with Last.fm</a>

<style>
  .connect { display: inline-block; background: var(--mauve); color: var(--base); font-weight: 600; padding: 0.6rem 1rem; border-radius: 8px; text-decoration: none; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test src/lib/stores/auth.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add src/lib/stores/auth.ts src/lib/components/ConnectButton.svelte src/routes/+layout.ts
git commit -m "feat: add auth store, connect button, SPA mode"
```

---

## Phase 3 — Presentational components

### Task 7: format helpers + SummaryCard + TopList

**Files:**
- Create: `frontend/src/lib/format.ts`, `frontend/src/lib/components/SummaryCard.svelte`, `frontend/src/lib/components/TopList.svelte`
- Test: `frontend/src/lib/format.test.ts`, `frontend/src/lib/components/TopList.test.ts`

**Interfaces:**
- Produces:
  - `format.ts`: `weekdayName(index: 0..6): string` (0→"Mon" … 6→"Sun"); `formatDateTime(iso: string): string` (locale short).
  - `<SummaryCard total={number} />` — renders a labelled total.
  - `<TopList title={string} items={{ label: string; count: number }[]} />` — ranked rows, each with an inline proportion bar (width = count/max).

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/src/lib/format.test.ts
import { describe, it, expect } from 'vitest';
import { weekdayName } from './format';

describe('weekdayName', () => {
  it('maps index 0 to Monday and 6 to Sunday', () => {
    expect(weekdayName(0)).toBe('Mon');
    expect(weekdayName(6)).toBe('Sun');
  });
});
```

```typescript
// frontend/src/lib/components/TopList.test.ts
import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import TopList from './TopList.svelte';

describe('TopList', () => {
  it('renders the title and ranked rows', () => {
    render(TopList, { props: { title: 'Top Artists', items: [
      { label: 'Daft Punk', count: 10 },
      { label: 'Kavinsky', count: 4 }
    ] } });
    expect(screen.getByRole('heading', { name: 'Top Artists' })).toBeInTheDocument();
    expect(screen.getByText('Daft Punk')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders an empty hint when there are no items', () => {
    render(TopList, { props: { title: 'Top Artists', items: [] } });
    expect(screen.getByText(/no data/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && pnpm test src/lib/format.test.ts src/lib/components/TopList.test.ts`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement**

```typescript
// frontend/src/lib/format.ts
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export function weekdayName(index: number): string {
  return WEEKDAYS[index] ?? '';
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}
```

```svelte
<!-- frontend/src/lib/components/SummaryCard.svelte -->
<script lang="ts">
  let { total }: { total: number } = $props();
</script>

<div class="card">
  <span class="value">{total.toLocaleString()}</span>
  <span class="label">total listens</span>
</div>

<style>
  .card { background: var(--surface); border-radius: 10px; padding: 1.25rem; display: flex; flex-direction: column; gap: 0.25rem; }
  .value { font-size: 2rem; font-weight: 700; color: var(--green); }
  .label { color: var(--subtext); }
</style>
```

```svelte
<!-- frontend/src/lib/components/TopList.svelte -->
<script lang="ts">
  let { title, items }: { title: string; items: { label: string; count: number }[] } = $props();
  const max = $derived(items.reduce((m, i) => Math.max(m, i.count), 0) || 1);
</script>

<section>
  <h2>{title}</h2>
  {#if items.length === 0}
    <p class="empty">No data yet.</p>
  {:else}
    <ol>
      {#each items as item (item.label)}
        <li>
          <span class="bar" style="width: {(item.count / max) * 100}%"></span>
          <span class="label">{item.label}</span>
          <span class="count">{item.count}</span>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  section { background: var(--surface); border-radius: 10px; padding: 1rem 1.25rem; }
  h2 { font-size: 1rem; color: var(--subtext); margin: 0 0 0.75rem; }
  ol { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; }
  li { position: relative; display: flex; align-items: center; gap: 0.5rem; padding: 0.35rem 0.5rem; border-radius: 6px; overflow: hidden; }
  .bar { position: absolute; inset: 0; background: var(--mauve); opacity: 0.18; z-index: 0; }
  .label { z-index: 1; flex: 1; }
  .count { z-index: 1; color: var(--subtext); font-variant-numeric: tabular-nums; }
  .empty { color: var(--subtext); }
</style>
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && pnpm test src/lib/format.test.ts src/lib/components/TopList.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add src/lib/format.ts src/lib/format.test.ts src/lib/components/SummaryCard.svelte src/lib/components/TopList.svelte src/lib/components/TopList.test.ts
git commit -m "feat: add format helpers, SummaryCard, TopList"
```

---

### Task 8: ListeningClock + WeekdayChart (LayerChart bar charts)

**Files:**
- Create: `frontend/src/lib/components/ListeningClock.svelte`, `frontend/src/lib/components/WeekdayChart.svelte`
- Test: `frontend/src/lib/components/WeekdayChart.test.ts`

**Interfaces:**
- Consumes: `weekdayName` from `format.ts`; LayerChart's `BarChart` (or `Chart` + `Bars`).
- Produces:
  - `<ListeningClock hours={number[]} />` — 24-bar chart, x = hour 0–23, y = count.
  - `<WeekdayChart days={number[]} />` — 7-bar chart, x = weekday name (index 0 = Mon), y = count.

- [ ] **Step 1: Write the failing test** (assert data-driven rendering, not pixels)

```typescript
// frontend/src/lib/components/WeekdayChart.test.ts
import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import WeekdayChart from './WeekdayChart.svelte';

describe('WeekdayChart', () => {
  it('renders a labelled region for the weekday distribution', () => {
    render(WeekdayChart, { props: { days: [3, 0, 1, 0, 5, 0, 2] } });
    // The chart exposes an accessible label + a total summary for non-visual users.
    expect(screen.getByRole('img', { name: /listens by weekday/i })).toBeInTheDocument();
    expect(screen.getByText(/11 listens/i)).toBeInTheDocument(); // 3+1+5+2 = 11
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test src/lib/components/WeekdayChart.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

For the LayerChart API, read the LayerChart docs/examples for the installed version (`pnpm why layerchart` to confirm version) — the declarative `BarChart` component takes `data` + `x`/`y` accessors. Wrap each chart in an element with `role="img"` and an `aria-label`, plus a visually-hidden total, so the component is testable and accessible.

```svelte
<!-- frontend/src/lib/components/WeekdayChart.svelte -->
<script lang="ts">
  import { BarChart } from 'layerchart';
  import { weekdayName } from '$lib/format';
  let { days }: { days: number[] } = $props();
  const data = $derived(days.map((count, i) => ({ day: weekdayName(i), count })));
  const total = $derived(days.reduce((a, b) => a + b, 0));
</script>

<figure role="img" aria-label="Listens by weekday">
  <figcaption>By weekday</figcaption>
  <div class="chart">
    <BarChart {data} x="day" y="count" />
  </div>
  <span class="sr-only">{total} listens</span>
</figure>

<style>
  figure { background: var(--surface); border-radius: 10px; padding: 1rem 1.25rem; margin: 0; }
  figcaption { color: var(--subtext); font-size: 1rem; margin-bottom: 0.5rem; }
  .chart { height: 200px; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
```

```svelte
<!-- frontend/src/lib/components/ListeningClock.svelte -->
<script lang="ts">
  import { BarChart } from 'layerchart';
  let { hours }: { hours: number[] } = $props();
  const data = $derived(hours.map((count, h) => ({ hour: `${h}`, count })));
  const total = $derived(hours.reduce((a, b) => a + b, 0));
</script>

<figure role="img" aria-label="Listens by hour of day">
  <figcaption>By hour (UTC)</figcaption>
  <div class="chart">
    <BarChart {data} x="hour" y="count" />
  </div>
  <span class="sr-only">{total} listens</span>
</figure>

<style>
  figure { background: var(--surface); border-radius: 10px; padding: 1rem 1.25rem; margin: 0; }
  figcaption { color: var(--subtext); font-size: 1rem; margin-bottom: 0.5rem; }
  .chart { height: 200px; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
```

If the installed LayerChart version's `BarChart` import path or props differ, adjust to the real API (keep the `figure[role=img]` wrapper + `.sr-only` total exactly as the test expects). If LayerChart cannot render under jsdom, wrap the `<BarChart>` in `{#if browser}` (import `browser` from `$app/environment`) so the test asserts the accessible label + total while the chart itself only mounts in the browser — the test must still pass.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test src/lib/components/WeekdayChart.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add src/lib/components/ListeningClock.svelte src/lib/components/WeekdayChart.svelte src/lib/components/WeekdayChart.test.ts
git commit -m "feat: add listening clock + weekday charts"
```

---

### Task 9: HistoryChart (time-series) with bucket selector

**Files:**
- Create: `frontend/src/lib/components/HistoryChart.svelte`
- Test: `frontend/src/lib/components/HistoryChart.test.ts`

**Interfaces:**
- Consumes: LayerChart's area/line chart; `HistoryPoint[]` (`{ period, count }`).
- Produces: `<HistoryChart points={HistoryPoint[]} bucket={Bucket} onBucketChange={(b: Bucket) => void} />` — a line/area chart of counts over time plus a `day | week | month` selector that calls `onBucketChange`.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/lib/components/HistoryChart.test.ts
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import HistoryChart from './HistoryChart.svelte';

describe('HistoryChart', () => {
  it('renders an accessible region and a bucket selector', async () => {
    const onBucketChange = vi.fn();
    render(HistoryChart, { props: {
      points: [{ period: '2024-06-01T00:00:00', count: 3 }, { period: '2024-06-02T00:00:00', count: 5 }],
      bucket: 'day',
      onBucketChange
    } });
    expect(screen.getByRole('img', { name: /listens over time/i })).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByRole('combobox', { name: /bucket/i }), 'week');
    expect(onBucketChange).toHaveBeenCalledWith('week');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test src/lib/components/HistoryChart.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```svelte
<!-- frontend/src/lib/components/HistoryChart.svelte -->
<script lang="ts">
  import { AreaChart } from 'layerchart';
  import { browser } from '$app/environment';
  import type { Bucket, HistoryPoint } from '$lib/api/client';

  let { points, bucket, onBucketChange }:
    { points: HistoryPoint[]; bucket: Bucket; onBucketChange: (b: Bucket) => void } = $props();

  const data = $derived(points.map((p) => ({ date: new Date(p.period), count: p.count })));

  function onChange(e: Event) {
    onBucketChange((e.currentTarget as HTMLSelectElement).value as Bucket);
  }
</script>

<figure role="img" aria-label="Listens over time">
  <div class="head">
    <figcaption>Over time</figcaption>
    <label>
      <span class="sr-only">Bucket</span>
      <select aria-label="Bucket" value={bucket} onchange={onChange}>
        <option value="day">Daily</option>
        <option value="week">Weekly</option>
        <option value="month">Monthly</option>
      </select>
    </label>
  </div>
  <div class="chart">
    {#if browser}
      <AreaChart {data} x="date" y="count" />
    {/if}
  </div>
</figure>

<style>
  figure { background: var(--surface); border-radius: 10px; padding: 1rem 1.25rem; margin: 0; }
  .head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
  figcaption { color: var(--subtext); font-size: 1rem; }
  select { background: var(--mantle); color: var(--text); border: 0; border-radius: 6px; padding: 0.3rem 0.5rem; }
  .chart { height: 240px; }
  .sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
</style>
```

(Adjust the LayerChart import/props to the installed version's real API if needed; keep the `figure[role=img]` label and the `combobox` selector exactly as the test expects. `{#if browser}` guards the chart so jsdom tests pass.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test src/lib/components/HistoryChart.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add src/lib/components/HistoryChart.svelte src/lib/components/HistoryChart.test.ts
git commit -m "feat: add history time-series chart with bucket selector"
```

---

### Task 10: RecentList

**Files:**
- Create: `frontend/src/lib/components/RecentList.svelte`
- Test: `frontend/src/lib/components/RecentList.test.ts`

**Interfaces:**
- Consumes: `RecentItem[]`, `formatDateTime`.
- Produces: `<RecentList items={RecentItem[]} />` — a list of recent scrobbles (track — artist, time).

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/lib/components/RecentList.test.ts
import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import RecentList from './RecentList.svelte';

describe('RecentList', () => {
  it('renders each recent track with its artist', () => {
    render(RecentList, { props: { items: [
      { track: 'Nightcall', artist: 'Kavinsky', album: 'OutRun', played_at: '2024-06-17T12:00:00Z' }
    ] } });
    expect(screen.getByText('Nightcall')).toBeInTheDocument();
    expect(screen.getByText('Kavinsky')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test src/lib/components/RecentList.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```svelte
<!-- frontend/src/lib/components/RecentList.svelte -->
<script lang="ts">
  import { formatDateTime } from '$lib/format';
  import type { RecentItem } from '$lib/api/client';
  let { items }: { items: RecentItem[] } = $props();
</script>

<section>
  <h2>Recent</h2>
  {#if items.length === 0}
    <p class="empty">No data yet.</p>
  {:else}
    <ul>
      {#each items as item (item.played_at + item.track)}
        <li>
          <span class="track">{item.track}</span>
          <span class="artist">{item.artist}</span>
          <time>{formatDateTime(item.played_at)}</time>
        </li>
      {/each}
    </ul>
  {/if}
</section>

<style>
  section { background: var(--surface); border-radius: 10px; padding: 1rem 1.25rem; }
  h2 { font-size: 1rem; color: var(--subtext); margin: 0 0 0.75rem; }
  ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 0.4rem; }
  li { display: grid; grid-template-columns: 1fr auto auto; gap: 0.75rem; align-items: baseline; }
  .artist { color: var(--subtext); }
  time { color: var(--subtext); font-variant-numeric: tabular-nums; }
  .empty { color: var(--subtext); }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test src/lib/components/RecentList.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add src/lib/components/RecentList.svelte src/lib/components/RecentList.test.ts
git commit -m "feat: add recent listens list"
```

---

## Phase 4 — Dashboard, sharing, public view

### Task 11: Dashboard component + home page wiring

**Files:**
- Create: `frontend/src/lib/components/Dashboard.svelte`
- Modify: `frontend/src/routes/+page.svelte`
- Test: `frontend/src/lib/components/Dashboard.test.ts`

**Interfaces:**
- Consumes: all stat `api.*` methods, `SummaryCard`, `TopList`, `ListeningClock`, `WeekdayChart`, `HistoryChart`, `RecentList`.
- Produces: `<Dashboard />` — loads all stats on mount and lays them out. `+page.svelte` shows `<Dashboard />` when `auth.user` is set, otherwise a `<ConnectButton />` landing; shows a loading state while `auth.loading`.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/lib/components/Dashboard.test.ts
import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import Dashboard from './Dashboard.svelte';
import { api } from '$lib/api/client';

describe('Dashboard', () => {
  it('loads and renders stats sections', async () => {
    vi.spyOn(api, 'summary').mockResolvedValue({ total_listens: 42 });
    vi.spyOn(api, 'topArtists').mockResolvedValue([{ artist: 'Daft Punk', count: 10 }]);
    vi.spyOn(api, 'topTracks').mockResolvedValue([{ track: 'Aerodynamic', count: 6 }]);
    vi.spyOn(api, 'topAlbums').mockResolvedValue([{ album: 'Discovery', count: 8 }]);
    vi.spyOn(api, 'clock').mockResolvedValue(new Array(24).fill(0));
    vi.spyOn(api, 'weekday').mockResolvedValue(new Array(7).fill(0));
    vi.spyOn(api, 'history').mockResolvedValue([{ period: '2024-06-01T00:00:00', count: 3 }]);
    vi.spyOn(api, 'recent').mockResolvedValue([]);

    render(Dashboard);
    await waitFor(() => expect(screen.getByText('42')).toBeInTheDocument());
    expect(screen.getByText('Daft Punk')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test src/lib/components/Dashboard.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```svelte
<!-- frontend/src/lib/components/Dashboard.svelte -->
<script lang="ts">
  import { api, type Bucket } from '$lib/api/client';
  import SummaryCard from './SummaryCard.svelte';
  import TopList from './TopList.svelte';
  import ListeningClock from './ListeningClock.svelte';
  import WeekdayChart from './WeekdayChart.svelte';
  import HistoryChart from './HistoryChart.svelte';
  import RecentList from './RecentList.svelte';

  let total = $state(0);
  let artists = $state<{ label: string; count: number }[]>([]);
  let tracks = $state<{ label: string; count: number }[]>([]);
  let albums = $state<{ label: string; count: number }[]>([]);
  let hours = $state<number[]>(new Array(24).fill(0));
  let days = $state<number[]>(new Array(7).fill(0));
  let history = $state<{ period: string; count: number }[]>([]);
  let recent = $state<{ track: string; artist: string; album: string | null; played_at: string }[]>([]);
  let bucket = $state<Bucket>('day');

  async function loadHistory(b: Bucket) {
    bucket = b;
    history = await api.history(b);
  }

  $effect(() => {
    (async () => {
      const [s, ar, tr, al, cl, wd, rc] = await Promise.all([
        api.summary(), api.topArtists(10), api.topTracks(10), api.topAlbums(10),
        api.clock(), api.weekday(), api.recent(20)
      ]);
      total = s.total_listens;
      artists = ar.map((x) => ({ label: x.artist, count: x.count }));
      tracks = tr.map((x) => ({ label: x.track, count: x.count }));
      albums = al.map((x) => ({ label: x.album, count: x.count }));
      hours = cl; days = wd; recent = rc;
      await loadHistory('day');
    })();
  });
</script>

<div class="grid">
  <SummaryCard {total} />
  <HistoryChart points={history} {bucket} onBucketChange={loadHistory} />
  <TopList title="Top Artists" items={artists} />
  <TopList title="Top Tracks" items={tracks} />
  <TopList title="Top Albums" items={albums} />
  <ListeningClock {hours} />
  <WeekdayChart {days} />
  <RecentList items={recent} />
</div>

<style>
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; padding: 1.5rem; }
</style>
```

```svelte
<!-- frontend/src/routes/+page.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { auth, loadMe } from '$lib/stores/auth';
  import Header from '$lib/components/Header.svelte';
  import ConnectButton from '$lib/components/ConnectButton.svelte';
  import Dashboard from '$lib/components/Dashboard.svelte';
  import ShareManager from '$lib/components/ShareManager.svelte';

  onMount(loadMe);
</script>

<Header>
  {#if $auth.user}<ShareManager />{/if}
</Header>

{#if $auth.loading}
  <p class="centered">Loading…</p>
{:else if $auth.user}
  <Dashboard />
{:else}
  <div class="landing">
    <h1>Your Tidal listening, tracked.</h1>
    <p>Connect your Last.fm account (where your Tidal scrobbles land) to see your stats.</p>
    <ConnectButton />
  </div>
{/if}

<style>
  .centered, .landing { text-align: center; padding: 4rem 1.5rem; }
  .landing h1 { color: var(--text); }
  .landing p { color: var(--subtext); }
</style>
```

> NOTE: `+page.svelte` imports `ShareManager` (Task 12). Implement this task and Task 12 together if executing strictly in order causes an import error — or stub `ShareManager` first. The subagent for this task should create a minimal `ShareManager.svelte` placeholder ONLY if Task 12 is not yet done; otherwise rely on Task 12's real component. (Recommended: do Task 12 before wiring `+page.svelte`, or temporarily remove the `ShareManager` usage and add it in Task 12.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test src/lib/components/Dashboard.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add src/lib/components/Dashboard.svelte src/routes/+page.svelte src/lib/components/Dashboard.test.ts
git commit -m "feat: add dashboard + home page wiring"
```

---

### Task 12: ShareManager

**Files:**
- Create: `frontend/src/lib/components/ShareManager.svelte`
- Test: `frontend/src/lib/components/ShareManager.test.ts`

**Interfaces:**
- Consumes: `api.createShare()`, `api.revokeShare(token)`.
- Produces: `<ShareManager />` — a "Share" button that creates a share and shows the public URL (`${location.origin}/shared/${token}`) with a copy action and a "Revoke" button.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/lib/components/ShareManager.test.ts
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import ShareManager from './ShareManager.svelte';
import { api } from '$lib/api/client';

describe('ShareManager', () => {
  it('creates a share and shows the public link', async () => {
    vi.spyOn(api, 'createShare').mockResolvedValue({ share_token: 'TOK123' });
    render(ShareManager);
    await userEvent.click(screen.getByRole('button', { name: /share/i }));
    const link = await screen.findByText(/\/s\/TOK123$/);
    expect(link).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test src/lib/components/ShareManager.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```svelte
<!-- frontend/src/lib/components/ShareManager.svelte -->
<script lang="ts">
  import { api } from '$lib/api/client';

  let token = $state<string | null>(null);
  let busy = $state(false);
  const shareUrl = $derived(token ? `${location.origin}/s/${token}` : null);

  async function createShare() {
    busy = true;
    try { token = (await api.createShare()).share_token; }
    finally { busy = false; }
  }
  async function revoke() {
    if (!token) return;
    await api.revokeShare(token);
    token = null;
  }
  async function copy() {
    if (shareUrl) await navigator.clipboard.writeText(shareUrl);
  }
</script>

{#if shareUrl}
  <span class="link">{shareUrl}</span>
  <button onclick={copy}>Copy</button>
  <button onclick={revoke}>Revoke</button>
{:else}
  <button onclick={createShare} disabled={busy}>Share</button>
{/if}

<style>
  .link { color: var(--blue); font-size: 0.85rem; }
  button { background: var(--surface); color: var(--text); border: 0; border-radius: 6px; padding: 0.4rem 0.6rem; cursor: pointer; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test src/lib/components/ShareManager.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add src/lib/components/ShareManager.svelte src/lib/components/ShareManager.test.ts
git commit -m "feat: add share manager"
```

---

### Task 13: Public shared dashboard route

**Files:**
- Create: `frontend/src/routes/s/[token]/+page.svelte`, `frontend/src/routes/s/[token]/+page.ts`
- Test: `frontend/src/routes/s/shared-page.test.ts`

(The public page route is `/s/{token}`; it reads from the backend's `/shared/{token}/*` API via `api.shared.*`.)

**Interfaces:**
- Consumes: `api.shared.*`, the presentational components (`SummaryCard`, `TopList`, `ListeningClock`, `WeekdayChart`, `HistoryChart`, `RecentList`).
- Produces: a public, no-auth route `/shared/{token}` rendering the same dashboard layout read-only (no ShareManager); shows a "link not found / revoked" message on 404.

- [ ] **Step 1: Write the failing test** (test the page component directly with a prop-provided token)

```typescript
// frontend/src/routes/s/shared-page.test.ts
import { render, screen, waitFor } from '@testing-library/svelte';
import { describe, it, expect, vi } from 'vitest';
import SharedPage from './[token]/+page.svelte';
import { api } from '$lib/api/client';

describe('shared dashboard page', () => {
  it('renders shared stats for a valid token', async () => {
    vi.spyOn(api.shared, 'summary').mockResolvedValue({ total_listens: 7 });
    vi.spyOn(api.shared, 'topArtists').mockResolvedValue([{ artist: 'Kavinsky', count: 3 }]);
    vi.spyOn(api.shared, 'topTracks').mockResolvedValue([]);
    vi.spyOn(api.shared, 'topAlbums').mockResolvedValue([]);
    vi.spyOn(api.shared, 'clock').mockResolvedValue(new Array(24).fill(0));
    vi.spyOn(api.shared, 'weekday').mockResolvedValue(new Array(7).fill(0));
    vi.spyOn(api.shared, 'history').mockResolvedValue([]);
    vi.spyOn(api.shared, 'recent').mockResolvedValue([]);

    render(SharedPage, { props: { data: { token: 'TOK' } } });
    await waitFor(() => expect(screen.getByText('7')).toBeInTheDocument());
    expect(screen.getByText('Kavinsky')).toBeInTheDocument();
  });

  it('shows a not-found message when the token is invalid', async () => {
    vi.spyOn(api.shared, 'summary').mockRejectedValue(new Error('404'));
    render(SharedPage, { props: { data: { token: 'BAD' } } });
    await waitFor(() => expect(screen.getByText(/not found|revoked/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && pnpm test src/routes/s/shared-page.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```typescript
// frontend/src/routes/s/[token]/+page.ts
import type { PageLoad } from './$types';

export const load: PageLoad = ({ params }) => {
  return { token: params.token };
};
```

```svelte
<!-- frontend/src/routes/s/[token]/+page.svelte -->
<script lang="ts">
  import { api, type Bucket } from '$lib/api/client';
  import Header from '$lib/components/Header.svelte';
  import SummaryCard from '$lib/components/SummaryCard.svelte';
  import TopList from '$lib/components/TopList.svelte';
  import ListeningClock from '$lib/components/ListeningClock.svelte';
  import WeekdayChart from '$lib/components/WeekdayChart.svelte';
  import HistoryChart from '$lib/components/HistoryChart.svelte';
  import RecentList from '$lib/components/RecentList.svelte';

  let { data }: { data: { token: string } } = $props();
  const token = data.token;

  let error = $state(false);
  let total = $state(0);
  let artists = $state<{ label: string; count: number }[]>([]);
  let tracks = $state<{ label: string; count: number }[]>([]);
  let albums = $state<{ label: string; count: number }[]>([]);
  let hours = $state<number[]>(new Array(24).fill(0));
  let days = $state<number[]>(new Array(7).fill(0));
  let history = $state<{ period: string; count: number }[]>([]);
  let recent = $state<{ track: string; artist: string; album: string | null; played_at: string }[]>([]);
  let bucket = $state<Bucket>('day');

  async function loadHistory(b: Bucket) {
    bucket = b;
    history = await api.shared.history(token, b);
  }

  $effect(() => {
    (async () => {
      try {
        const [s, ar, tr, al, cl, wd, rc] = await Promise.all([
          api.shared.summary(token), api.shared.topArtists(token), api.shared.topTracks(token),
          api.shared.topAlbums(token), api.shared.clock(token), api.shared.weekday(token), api.shared.recent(token)
        ]);
        total = s.total_listens;
        artists = ar.map((x) => ({ label: x.artist, count: x.count }));
        tracks = tr.map((x) => ({ label: x.track, count: x.count }));
        albums = al.map((x) => ({ label: x.album, count: x.count }));
        hours = cl; days = wd; recent = rc;
        await loadHistory('day');
      } catch {
        error = true;
      }
    })();
  });
</script>

<Header />

{#if error}
  <p class="centered">This shared link was not found or has been revoked.</p>
{:else}
  <div class="grid">
    <SummaryCard {total} />
    <HistoryChart points={history} {bucket} onBucketChange={loadHistory} />
    <TopList title="Top Artists" items={artists} />
    <TopList title="Top Tracks" items={tracks} />
    <TopList title="Top Albums" items={albums} />
    <ListeningClock {hours} />
    <WeekdayChart {days} />
    <RecentList items={recent} />
  </div>
{/if}

<style>
  .centered { text-align: center; padding: 4rem 1.5rem; color: var(--subtext); }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; padding: 1.5rem; }
</style>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && pnpm test src/routes/s/shared-page.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add src/routes/s/
git commit -m "feat: add public shared dashboard route at /s/{token}"
```

---

### Task 14: Build check + Playwright E2E smoke

**Files:**
- Create: `frontend/playwright.config.ts`, `frontend/tests/e2e/smoke.spec.ts`

**Interfaces:**
- Produces: a passing production build (`pnpm build`) and a Playwright smoke test that the landing page renders the connect call-to-action when the API reports anonymous.

- [ ] **Step 1: Verify the production build succeeds**

Run: `cd frontend && pnpm build`
Expected: build completes, `build/index.html` exists. Fix any type/import errors surfaced (also run `pnpm check`).

- [ ] **Step 2: Write the Playwright config + smoke test**

```typescript
// frontend/playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: 'tests/e2e',
  use: { baseURL: 'http://localhost:4173' },
  webServer: {
    command: 'pnpm build && pnpm preview --port 4173',
    port: 4173,
    reuseExistingServer: !process.env.CI
  }
});
```

```typescript
// frontend/tests/e2e/smoke.spec.ts
import { test, expect } from '@playwright/test';

test('landing shows connect CTA when anonymous', async ({ page }) => {
  // /auth/me has no backend in preview → intercept it as 401 (anonymous).
  await page.route('**/auth/me', (route) => route.fulfill({ status: 401, body: '{"detail":"no"}' }));
  await page.goto('/');
  await expect(page.getByRole('link', { name: /connect with last\.fm/i })).toBeVisible();
});
```

- [ ] **Step 3: Add `@playwright/test` and run the E2E**

Run:
```bash
cd /root/git/tidalwave/frontend
pnpm add -D @playwright/test
pnpm exec playwright install chromium
pnpm test:e2e
```
Expected: 1 passing E2E test. (If the sandbox cannot launch a browser, report this in your status and confirm `pnpm build` + the unit suite pass instead — do not delete the E2E test.)

- [ ] **Step 4: Run the full unit suite + check**

Run: `cd frontend && pnpm test && pnpm check`
Expected: all unit tests pass; `svelte-check` reports 0 errors.

- [ ] **Step 5: Commit**

```bash
cd /root/git/tidalwave/frontend
git add playwright.config.ts tests/ package.json pnpm-lock.yaml
git commit -m "test: add production build check + Playwright smoke"
```

---

## Self-Review Notes (for the implementer)

- **Spec coverage:** This plan delivers the spec's frontend: gated dashboard (Task 11) behind Last.fm connect (Task 6), Catppuccin theming (Task 5), all stat views incl. clock/weekday/history (Tasks 7–10), recent (Task 10), and shareable read-only public dashboards (Tasks 12–13). Supporting backend endpoints `/auth/me` and the full `/shared/*` surface are Tasks 1–2.
- **Cross-task type consistency:** the app-facing types live in `client.ts` (`UserInfo`, `ArtistCount`, `TrackCount`, `AlbumCount`, `HistoryPoint`, `RecentItem`, `Bucket`); components consume those exact names. `TopList` takes a generic `{ label, count }`, so the dashboard maps `artist`/`track`/`album` → `label` at the call site.
- **LayerChart risk:** the exact LayerChart import paths/props vary by version. Tasks 8–9 pin the *testable contract* (an accessible `figure[role=img]` + a total / a `combobox`) and guard the chart with `{#if browser}` so jsdom tests never depend on canvas/SVG internals. The implementer finalizes the real chart props against the installed version.
- **Ordering caveat:** `+page.svelte` (Task 11) imports `ShareManager` (Task 12). Do Task 12 before wiring, or follow the note in Task 11.
- **Tooling:** Node ≥ 22.12 + pnpm must be bootstrapped first (Task 3, Step 1); the environment ships Node 20 only.
