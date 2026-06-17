# tidalwave — Listening Tracker (Design Spec)

**Datum:** 2026-06-17
**Status:** Design genehmigt, bereit für Implementierungsplan

## Zusammenfassung

`tidalwave` ist ein selbst-gehostetes, **mehrbenutzerfähiges** Listening-History-Tracking-
Tool im Geist von [your_spotify](https://github.com/Yooooomi/your_spotify) — aber für
**Tidal-Nutzer**.

Es ist ein **eigenständiges Projekt** (eigenes Repo), unabhängig von `linkhop`, mit
demselben Tech-Stack. Datenquelle ist **Last.fm**, nicht Tidal direkt. Jeder Nutzer
verbindet sein eigenes Last.fm-Konto und sieht ausschließlich seine eigenen Daten.

## Kernentscheidung: Warum Last.fm statt Tidal-API

Eine „your_spotify für Tidal" über die **offizielle Tidal-API ist nicht machbar**:

- Tidals Open API (v2) hat **keinen** `recently-played` / Listening-History / Play-Log-
  Endpoint. Tidal-Maintainer (Aug. 2024): *„This functionality is unfortunately
  currently not planned."* ([tidal-music/discussions/10](https://github.com/orgs/tidal-music/discussions/10))
- Now-Playing/Playback ist **nur über die SDKs** verfügbar, nicht als server-seitig
  pollbarer REST-Endpoint.
- Der etablierte Weg im Ökosystem: **Tidal → Last.fm scrobbeln** (native Tidal↔Last.fm-
  Verbindung oder ein Scrobbler), die History liegt dann bei Last.fm, das eine saubere
  öffentliche API hat (`user.getRecentTracks`).

`tidalwave` ist daher technisch ein **Scrobble-Ingest- + Analytics-Tool**, das seine Daten
aus Last.fm zieht. Damit ist der Code-Reuse aus `linkhop` praktisch null (andere Quelle,
anderes Auth-Modell, stateful statt stateless) — was die Entscheidung für ein **eigenes
Repo** bestätigt. linkhops „no-trackers"-Identität bleibt zudem unberührt.

## Architektur

```
Tidal-App  ──scrobbelt──►  Last.fm  ◄──pollt──  [Ingest-Poller]
                                                       │ upsert
                                                       ▼
                                              Postgres (listens)
                                                       │ aggregiert
                                                       ▼
                                          FastAPI /stats  ◄──  SvelteKit-Dashboards
```

Last.fm ist die einzige externe Abhängigkeit. Redis ist optional (nur falls Stats-Caching
nötig wird — V1 voraussichtlich nicht).

### Stack (gespiegelt von linkhop)

| Layer    | Tech                                                          |
| -------- | ------------------------------------------------------------- |
| Backend  | Python 3.12 (uv), FastAPI, SQLAlchemy 2 (async), asyncpg, Alembic |
| Frontend | SvelteKit (`adapter-static`), TypeScript, Vite                |
| Datenbank| Postgres 16 (CNPG in Produktion)                              |
| Tests    | pytest, Playwright (E2E), Vitest (Komponenten)                |
| Packaging| Docker-Images, Helm-Chart                                     |
| Deploy   | FluxCD → RKE2 + Traefik + cert-manager + external-dns         |

## Komponenten

Jede Einheit hat einen klaren Zweck und eine definierte Schnittstelle:

1. **Last.fm-Client** — dünner Wrapper um die Last.fm-API. Methoden: `auth.getSession`
   (Connect), `user.getRecentTracks` (Ingest/Backfill). Verbirgt Signierung (`api_sig`),
   Paginierung und Rate-Limit-Handling. Testbar mit gemockten HTTP-Antworten.
2. **Ingest-Poller** — periodischer Job (~1–5 min). Holt für jeden verbundenen User die
   neuen Scrobbles seit `sync_state.last_played_at` und schreibt sie idempotent. Erkennt
   „now playing" über Last.fms `nowplaying`-Flag (wird *nicht* als finaler Listen
   gespeichert, bis er abgeschlossen ist).
3. **Backfill** — einmaliger, wiederholbarer Import der kompletten History per
   paginiertem `user.getRecentTracks`. Idempotent über den Dedup-Key.
4. **Stats-API** — FastAPI-Endpoints: Top Tracks/Artists/Albums je Zeitraum,
   Listening-Clock (Stunde/Wochentag), Scrobble-Verlauf, Gesamtzahlen.
5. **Auth-/Connect-Routen** — `/auth/login` (Redirect zu Last.fm), `/auth/callback`
   (Token → Session-Key), Session-Handling, Share-Token-Verwaltung.
6. **Frontend** — SvelteKit-Dashboards (Charts), gleiche Catppuccin-Mocha/Latte-Optik
   wie linkhop.

## Datenmodell

Mehrbenutzerfähig von Tag 1 — jede Tabelle ist über `user_id` getrennt; ein Nutzer kann
niemals Daten eines anderen sehen.

- **`users`** — `id`, `lastfm_username` (unique), `lastfm_session_key`, `is_admin` (bool;
  erster verbundener Account = Admin, für künftige Instanz-Verwaltung), `created_at`.
- **`listens`** — `id`, `user_id`, `track_title`, `artist`, `album`, `played_at` (UTC,
  indiziert), optionale Last.fm-MBIDs (`track_mbid`, `artist_mbid`, `album_mbid`).
  **Dedup-Key:** `UNIQUE (user_id, artist, track_title, played_at)` → Re-Polling und
  Backfill kollidieren nie.
- **`sync_state`** — `user_id` (PK), `last_played_at`, `last_synced_at`.
- **`shares`** — `id`, `share_token` (zufällig, URL-safe), `user_id`, optional
  `range_from`/`range_to`, `created_at`, `revoked_at` (nullable).

## Auth, Zugang & Sharing

### Connect-Flow (OAuth-ähnlich, via Last.fm Web-Auth)

1. `/auth/login` leitet zu `https://www.last.fm/api/auth/?api_key=<key>&cb=<callback>`.
2. User autorisiert auf Last.fm → Redirect zu `/auth/callback?token=<token>`.
3. Backend ruft `auth.getSession` (signiert mit `api_sig` = MD5 aus
   `api_key + method + token + secret`) → erhält **permanenten Session-Key**.
4. **Connect = Account-Erstellung + Login:** existiert noch kein User mit diesem
   `lastfm_username`, wird ein Account angelegt (sonst eingeloggt). Session-Key wird
   gespeichert, eine App-Session (Cookie) etabliert. Kein separates Passwort — die
   Last.fm-Identität *ist* der Account.

Vorteil ggü. Spotify-OAuth: Der Last.fm-Session-Key **läuft nie ab** — kein
Refresh-Token-Handling. History-Reads laufen mit dem Session-Key und funktionieren auch
bei **privaten** Profilen.

### Konfiguration

- App-weit: Last.fm **`API_KEY` + `API_SECRET`** (Env-Vars).
- **`REGISTRATION_MODE`** (Env): `open` (jeder kann sich per Connect registrieren) oder
  `allowlist` (nur vorab erlaubte Last.fm-Usernames). Default für eine öffentlich
  erreichbare Instanz: `allowlist`.
- Der erste verbundene Account erhält `is_admin=true`.

### Zugang (gated) + Sharing

- **Mehrbenutzer, gated:** Jeder Nutzer ist eingeloggt und sieht **ausschließlich seine
  eigenen** Dashboards. Alle Stats-Endpoints sind streng nach der `user_id` der Session
  gefiltert — ein Nutzer kann nie fremde Daten sehen.
- **Sharing (wie your_spotify):** Jeder Nutzer kann eigene **Share-Links** erstellen — ein
  zufälliges `share_token` gewährt öffentlichen, **read-only**-Zugriff auf *seine*
  Dashboards (optional auf einen Zeitraum begrenzt). Aufruf über `/share/<token>` rendert
  die Dashboards ohne Login. Links sind widerrufbar (`revoked_at`).

## Fehlerbehandlung

- **Last.fm-Rate-Limits:** Exponentielles Backoff + Retry im Last.fm-Client.
- **Übersprungene Polls:** Über `sync_state.last_played_at` wird beim nächsten Lauf
  lückenlos nachgeholt — der Poller ist zustandslos zwischen Läufen.
- **Doppelte Scrobbles:** Durch den `UNIQUE`-Dedup-Key auf DB-Ebene abgefangen
  (Insert-on-conflict-do-nothing).
- **Ungültiger/widerrufener Session-Key:** User wird als „disconnected" markiert; Poller
  überspringt ihn; UI fordert Re-Connect an.

## Tests

- **Backend:** pytest mit gemockten Last.fm-Antworten (Client hinter einem schmalen
  Interface, analog zu linkhops Adapter-Pattern). Abgedeckt: Signierung, Paginierung,
  Dedup/Idempotenz, Poller-State-Fortschritt, Backfill-Wiederholbarkeit, Share-Token-
  Zugriffskontrolle.
- **Frontend:** Vitest (Komponenten), Playwright (E2E: Connect-Flow, Dashboard-Rendering,
  Share-Link-Aufruf).

## MVP-Scope

**Drin:**
- Last.fm Connect-Flow (OAuth-artig) = Account-Erstellung + Login + Session-Handling
- **Mehrbenutzer:** mehrere Accounts, je Nutzer eigene Daten; `REGISTRATION_MODE`
  (`open`/`allowlist`)
- Ingest-Poller (über alle verbundenen User) + einmaliger Backfill pro User
- `listens`-Speicherung mit Dedup, strikt nach `user_id` getrennt
- Stats-API: Top Tracks/Artists/Albums je Zeitraum, Listening-Clock, Verlauf, Gesamtzahlen
- Ein Dashboard (SvelteKit, Catppuccin)
- Gated-Zugang + widerrufbare Share-Links pro Nutzer

**Raus für V1 (YAGNI):**
- Admin-/Instanz-Verwaltungs-UI (Account-Management läuft V1 über Env-Config + Connect)
- ListenBrainz als alternative Quelle
- Genre-Analysen
- „Wrapped"-Style-Jahresrückblicke
- Echtzeit-Now-Playing-Widget

## Offene Punkte für den Implementierungsplan

- Genaue Poll-Frequenz und ob der Poller als FastAPI-Background-Task, separater Worker
  oder Kubernetes-CronJob läuft.
- Konkrete Chart-Bibliothek im Frontend.
- Exakte Felder/Zeiträume der Stats-Endpoints.
