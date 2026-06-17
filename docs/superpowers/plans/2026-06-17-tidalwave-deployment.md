# tidalwave Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make tidalwave deployable: Docker images for backend + frontend, a Helm chart (backend, frontend, migration Job, **poller CronJob**, Ingress, Secret), and GitHub Actions CI mirroring the sibling `linkhop` project.

**Architecture:** Mirror linkhop's deployment exactly where possible — multi-stage Dockerfiles (uv-based backend, pnpm+nginx frontend), a Helm chart with the same `_helpers.tpl`/labels/secret conventions, and chart-releaser + image-publish workflows. tidalwave-specific differences: no Redis subchart; Last.fm/session/registration config instead of linkhop's service credentials; a poller CronJob that runs `tidalwave-poll` on a schedule; health path `/health`; Ingress routes the four backend prefixes (`/auth`, `/stats`, `/shares`, `/shared`) to the backend and everything else to the frontend.

**Tech Stack:** Docker, Helm 3, Kubernetes (RKE2 + Traefik + cert-manager + external-dns target), CNPG (external Postgres), GitHub Actions + `helm/chart-releaser-action`.

## Global Constraints

- Reference implementation to mirror: `/root/git/linkhop/` — its `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`, `helm/linkhop/**`, and `.github/workflows/{backend,frontend,helm}.yml`. Read these and adapt; do not invent structure that diverges without reason.
- Naming substitution everywhere: `linkhop` → `tidalwave`, `LINKHOP_` → `TIDALWAVE_`.
- Backend runtime: Python 3.12, `uv`, package `tidalwave`, ASGI app `tidalwave.main:app`, port 8080, health path **`/health`**. Alembic config is `alembic.ini` + the **`migrations/`** directory (NOT `alembic/`).
- The chart has **no Redis**. Postgres is external (CNPG-managed), supplied via `TIDALWAVE_DATABASE_URL`.
- Required runtime secrets: `TIDALWAVE_DATABASE_URL`, `TIDALWAVE_LASTFM_API_KEY`, `TIDALWAVE_LASTFM_API_SECRET`, `TIDALWAVE_SESSION_SECRET`. Non-secret config: `TIDALWAVE_LOG_LEVEL`, `TIDALWAVE_PUBLIC_BASE_URL`, `TIDALWAVE_REGISTRATION_MODE`, `TIDALWAVE_REGISTRATION_ALLOWLIST`.
- **Tooling availability in this environment:** Docker is NOT available — `docker build` cannot be validated locally; validate Dockerfiles by review + confirming every referenced path exists, and rely on CI for the real build. Helm CAN be installed (official script) — use `helm lint` and `helm template` as the verification gate for chart tasks.

---

## File Structure

```
backend/Dockerfile
frontend/Dockerfile
frontend/nginx.conf
helm/tidalwave/
  Chart.yaml
  .helmignore
  values.yaml
  templates/
    _helpers.tpl
    secret.yaml
    backend-deployment.yaml
    backend-service.yaml
    frontend-deployment.yaml
    frontend-service.yaml
    migration-job.yaml
    poller-cronjob.yaml        # tidalwave-specific
    ingress.yaml
    NOTES.txt
.github/workflows/
  backend.yml
  frontend.yml
  helm.yml
README.md                       # repo root: deploy + architecture overview
```

---

## Task 1: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Adapt linkhop's backend Dockerfile**

Read `/root/git/linkhop/backend/Dockerfile`. Create `backend/Dockerfile` as a copy with these exact changes:
- Replace every `linkhop` with `tidalwave` (the `useradd` user, comments).
- Remove the `LINKHOP_FORWARDED_ALLOW_IPS=127.0.0.1` ENV line (tidalwave doesn't use it).
- The final-stage copy of migrations: linkhop copies `alembic.ini` + `alembic/`. tidalwave copies `alembic.ini` + **`migrations/`**:
  ```dockerfile
  COPY alembic.ini ./alembic.ini
  COPY migrations ./migrations
  ```
- HEALTHCHECK uses tidalwave's health path **`/health`** (not `/api/v1/health`):
  ```dockerfile
  HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
      CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()" || exit 1
  ```
- CMD runs tidalwave's app with proxy headers (trusting the ingress); no env-var indirection:
  ```dockerfile
  CMD ["uvicorn", "tidalwave.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips=*"]
  ```
- Keep the two-stage `uv sync --locked` structure and `PATH="/app/.venv/bin:$PATH"` exactly as linkhop has it.

- [ ] **Step 2: Validate (no docker daemon here)**

Run: `cd /root/git/tidalwave/backend && ls alembic.ini migrations pyproject.toml uv.lock src/tidalwave/main.py`
Expected: all listed paths exist (they are what the Dockerfile COPYs / runs). Then re-read the Dockerfile and confirm every `COPY` source exists and the CMD module path is correct. Note in your report that the actual `docker build` is deferred to CI (no docker daemon in this environment).

- [ ] **Step 3: Commit**

```bash
cd /root/git/tidalwave
git add backend/Dockerfile
git commit -m "build: add backend Dockerfile"
```

---

## Task 2: Frontend Dockerfile + nginx.conf

**Files:**
- Create: `frontend/Dockerfile`, `frontend/nginx.conf`

**Interfaces:**
- Produces a static nginx image serving the SvelteKit `build/` SPA. **API routing is handled by the Ingress** (Task 8), so nginx only serves static assets + SPA fallback — it does NOT proxy the API.

- [ ] **Step 1: Adapt linkhop's frontend Dockerfile**

Read `/root/git/linkhop/frontend/Dockerfile`. Create `frontend/Dockerfile` as a copy unchanged except it already works for any SvelteKit `adapter-static` app (it builds with pnpm and copies `build/` into nginx). Confirm it references `package.json pnpm-lock.yaml pnpm-workspace.yaml`. tidalwave has no `pnpm-workspace.yaml` (single package), so adjust the COPY line to only the files that exist:
```dockerfile
COPY package.json pnpm-lock.yaml ./
```
Keep the rest (`corepack enable`, `pnpm install --frozen-lockfile`, `COPY . .`, `pnpm build`, nginx stage copying `/app/build` → `/usr/share/nginx/html` and `nginx.conf`).

- [ ] **Step 2: Create nginx.conf (SPA only — copy linkhop's verbatim)**

Read `/root/git/linkhop/frontend/nginx.conf` and copy it verbatim to `frontend/nginx.conf` (it serves static assets with long cache + SPA fallback to `/index.html`; no API proxying — that's the Ingress's job). No changes needed.

- [ ] **Step 3: Validate (no docker daemon here)**

Run: `cd /root/git/tidalwave/frontend && ls package.json && test -f pnpm-lock.yaml && echo "lockfile present" || echo "NOTE: run pnpm install (frontend plan) first to create pnpm-lock.yaml"`
Expected: `package.json` exists; `pnpm-lock.yaml` should exist after the frontend plan ran `pnpm install`. Confirm the Dockerfile's COPY sources all exist. Note that `docker build` is deferred to CI.

- [ ] **Step 4: Commit**

```bash
cd /root/git/tidalwave
git add frontend/Dockerfile frontend/nginx.conf
git commit -m "build: add frontend Dockerfile + nginx config"
```

---

## Task 3: Helm chart skeleton (Chart.yaml, _helpers.tpl, values.yaml, .helmignore)

**Files:**
- Create: `helm/tidalwave/Chart.yaml`, `helm/tidalwave/.helmignore`, `helm/tidalwave/templates/_helpers.tpl`, `helm/tidalwave/values.yaml`

**Interfaces:**
- Produces a chart that `helm lint`s clean (templates added in Task 4). `_helpers.tpl` defines `tidalwave.name`, `tidalwave.fullname`, `tidalwave.labels`, `tidalwave.selectorLabels`, `tidalwave.backendSelectorLabels`, `tidalwave.frontendSelectorLabels`, `tidalwave.secretName` (mirror linkhop, minus the Redis URL helper).

- [ ] **Step 1: Install Helm** (if not present)

Run: `helm version 2>/dev/null || (curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash)` then `helm version`.
Expected: Helm 3 reports a version.

- [ ] **Step 2: Create Chart.yaml** (no Redis dependency)

```yaml
# helm/tidalwave/Chart.yaml
apiVersion: v2
name: tidalwave
description: Self-hosted multi-user Tidal listening tracker (via Last.fm)
type: application
version: 0.1.0
appVersion: "0.1.0"
```

- [ ] **Step 3: Create .helmignore** — copy `/root/git/linkhop/helm/linkhop/.helmignore` verbatim to `helm/tidalwave/.helmignore`.

- [ ] **Step 4: Create _helpers.tpl** — copy `/root/git/linkhop/helm/linkhop/templates/_helpers.tpl`, replace all `linkhop` → `tidalwave`, and **delete the `tidalwave.redisUrl` helper block entirely** (the last define). Keep `name`, `fullname`, `labels`, `selectorLabels`, `backendSelectorLabels`, `frontendSelectorLabels`, `secretName`.

- [ ] **Step 5: Create values.yaml**

```yaml
# helm/tidalwave/values.yaml
# -- Backend
backend:
  image:
    repository: ghcr.io/OWNER/tidalwave-backend
    # -- Defaults to Chart.appVersion
    tag: ""
    pullPolicy: IfNotPresent
  replicas: 1
  resources: {}
  nodeSelector: {}
  tolerations: []
  affinity: {}

# -- Frontend
frontend:
  image:
    repository: ghcr.io/OWNER/tidalwave-frontend
    # -- Defaults to Chart.appVersion
    tag: ""
    pullPolicy: IfNotPresent
  replicas: 1
  resources: {}
  nodeSelector: {}
  tolerations: []
  affinity: {}

# -- Poller CronJob (runs `tidalwave-poll`)
poller:
  enabled: true
  # -- Cron schedule; default every 5 minutes
  schedule: "*/5 * * * *"

# -- Ingress
ingress:
  enabled: true
  className: ""
  host: ""
  annotations: {}
  tls:
    enabled: false
    secretName: ""

# -- Application config (non-sensitive)
config:
  logLevel: INFO
  # -- External URL of the site; used to build the Last.fm OAuth callback and
  # to decide whether the session cookie is marked Secure (https).
  publicBaseUrl: ""
  # -- "open" (anyone may register on connect) or "allowlist"
  registrationMode: allowlist
  # -- Comma-separated Last.fm usernames allowed to register (allowlist mode)
  registrationAllowlist: ""

# -- Sensitive credentials
secrets:
  databaseUrl: ""
  lastfmApiKey: ""
  lastfmApiSecret: ""
  sessionSecret: ""
  # -- Use an existing Secret instead of creating one. It must contain keys:
  # TIDALWAVE_DATABASE_URL, TIDALWAVE_LASTFM_API_KEY,
  # TIDALWAVE_LASTFM_API_SECRET, TIDALWAVE_SESSION_SECRET
  existingSecret: ""

# -- Alembic migrations (pre-install/pre-upgrade hook)
migration:
  enabled: true

imagePullSecrets: []
nameOverride: ""
fullnameOverride: ""
```

- [ ] **Step 6: Lint (templates absent yet — expect a chart-without-templates warning, no errors)**

Run: `cd /root/git/tidalwave && helm lint helm/tidalwave`
Expected: `1 chart(s) linted, 0 chart(s) failed` (a "no templates" info/warning is fine at this stage; there must be no errors).

- [ ] **Step 7: Commit**

```bash
cd /root/git/tidalwave
git add helm/tidalwave/Chart.yaml helm/tidalwave/.helmignore helm/tidalwave/values.yaml helm/tidalwave/templates/_helpers.tpl
git commit -m "feat: add Helm chart skeleton (no Redis)"
```

---

## Task 4: Helm templates (deployments, services, secret, migration, poller, ingress, NOTES)

**Files:**
- Create: `helm/tidalwave/templates/{secret,backend-deployment,backend-service,frontend-deployment,frontend-service,migration-job,poller-cronjob,ingress,NOTES.txt}.yaml`

**Interfaces:**
- Consumes the `_helpers.tpl` defines and `values.yaml` from Task 3.
- Produces a chart that renders cleanly with `helm template`.

- [ ] **Step 1: secret.yaml**

```yaml
# helm/tidalwave/templates/secret.yaml
{{- if not .Values.secrets.existingSecret }}
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "tidalwave.fullname" . }}
  labels:
    {{- include "tidalwave.labels" . | nindent 4 }}
type: Opaque
stringData:
  TIDALWAVE_DATABASE_URL: {{ required "secrets.databaseUrl is required" .Values.secrets.databaseUrl | quote }}
  TIDALWAVE_LASTFM_API_KEY: {{ .Values.secrets.lastfmApiKey | quote }}
  TIDALWAVE_LASTFM_API_SECRET: {{ .Values.secrets.lastfmApiSecret | quote }}
  TIDALWAVE_SESSION_SECRET: {{ required "secrets.sessionSecret is required" .Values.secrets.sessionSecret | quote }}
{{- end }}
```

- [ ] **Step 2: backend-deployment.yaml** — adapt linkhop's `backend-deployment.yaml`: `linkhop`→`tidalwave`, `envFrom` the secret, the `env` block becomes tidalwave's config vars, and probes use `/health`:

```yaml
# helm/tidalwave/templates/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "tidalwave.fullname" . }}-backend
  labels:
    {{- include "tidalwave.labels" . | nindent 4 }}
    app.kubernetes.io/component: backend
spec:
  replicas: {{ .Values.backend.replicas }}
  selector:
    matchLabels:
      {{- include "tidalwave.backendSelectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "tidalwave.backendSelectorLabels" . | nindent 8 }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: backend
          image: "{{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.backend.image.pullPolicy }}
          ports:
            - name: http
              containerPort: 8080
              protocol: TCP
          envFrom:
            - secretRef:
                name: {{ include "tidalwave.secretName" . }}
          env:
            - name: TIDALWAVE_LOG_LEVEL
              value: {{ .Values.config.logLevel | quote }}
            - name: TIDALWAVE_PUBLIC_BASE_URL
              value: {{ required "config.publicBaseUrl is required" .Values.config.publicBaseUrl | quote }}
            - name: TIDALWAVE_REGISTRATION_MODE
              value: {{ .Values.config.registrationMode | quote }}
            - name: TIDALWAVE_REGISTRATION_ALLOWLIST
              value: {{ .Values.config.registrationAllowlist | quote }}
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 30
            timeoutSeconds: 3
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
          {{- with .Values.backend.resources }}
          resources:
            {{- toYaml . | nindent 12 }}
          {{- end }}
      {{- with .Values.backend.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.backend.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.backend.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
```

- [ ] **Step 3: backend-service.yaml, frontend-deployment.yaml, frontend-service.yaml** — copy the three from `/root/git/linkhop/helm/linkhop/templates/` and replace `linkhop`→`tidalwave` throughout. (The frontend deployment/service need no tidalwave-specific env; they serve static files on port 80.)

- [ ] **Step 4: migration-job.yaml** — adapt linkhop's: `linkhop`→`tidalwave`, the env var is `TIDALWAVE_DATABASE_URL`:

```yaml
# helm/tidalwave/templates/migration-job.yaml
{{- if .Values.migration.enabled }}
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "tidalwave.fullname" . }}-migrate
  labels:
    {{- include "tidalwave.labels" . | nindent 4 }}
    app.kubernetes.io/component: migration
  annotations:
    helm.sh/hook: pre-install,pre-upgrade
    helm.sh/hook-weight: "-5"
    helm.sh/hook-delete-policy: before-hook-creation
spec:
  backoffLimit: 1
  template:
    metadata:
      labels:
        {{- include "tidalwave.backendSelectorLabels" . | nindent 8 }}
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      restartPolicy: Never
      containers:
        - name: migrate
          image: "{{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.backend.image.pullPolicy }}
          command: ["alembic", "upgrade", "head"]
          workingDir: /app
          envFrom:
            - secretRef:
                name: {{ include "tidalwave.secretName" . }}
{{- end }}
```

(Note: using `envFrom` the secret gives the job `TIDALWAVE_DATABASE_URL` whether the secret is generated or `existingSecret`.)

- [ ] **Step 5: poller-cronjob.yaml** (tidalwave-specific)

```yaml
# helm/tidalwave/templates/poller-cronjob.yaml
{{- if .Values.poller.enabled }}
apiVersion: batch/v1
kind: CronJob
metadata:
  name: {{ include "tidalwave.fullname" . }}-poller
  labels:
    {{- include "tidalwave.labels" . | nindent 4 }}
    app.kubernetes.io/component: poller
spec:
  schedule: {{ .Values.poller.schedule | quote }}
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 1
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 0
      template:
        metadata:
          labels:
            {{- include "tidalwave.backendSelectorLabels" . | nindent 12 }}
        spec:
          {{- with .Values.imagePullSecrets }}
          imagePullSecrets:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          restartPolicy: Never
          containers:
            - name: poller
              image: "{{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag | default .Chart.AppVersion }}"
              imagePullPolicy: {{ .Values.backend.image.pullPolicy }}
              command: ["tidalwave-poll"]
              envFrom:
                - secretRef:
                    name: {{ include "tidalwave.secretName" . }}
              env:
                - name: TIDALWAVE_LOG_LEVEL
                  value: {{ .Values.config.logLevel | quote }}
{{- end }}
```

- [ ] **Step 6: ingress.yaml** — route the four backend prefixes to the backend, everything else to the frontend:

```yaml
# helm/tidalwave/templates/ingress.yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "tidalwave.fullname" . }}
  labels:
    {{- include "tidalwave.labels" . | nindent 4 }}
  {{- with .Values.ingress.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  {{- if .Values.ingress.className }}
  ingressClassName: {{ .Values.ingress.className | quote }}
  {{- end }}
  {{- if .Values.ingress.tls.enabled }}
  tls:
    - hosts:
        - {{ .Values.ingress.host | quote }}
      secretName: {{ .Values.ingress.tls.secretName | quote }}
  {{- end }}
  rules:
    - host: {{ .Values.ingress.host | quote }}
      http:
        paths:
          {{- range $p := (list "/auth" "/stats" "/shares" "/shared") }}
          - path: {{ $p }}
            pathType: Prefix
            backend:
              service:
                name: {{ include "tidalwave.fullname" $ }}-backend
                port:
                  number: 8080
          {{- end }}
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "tidalwave.fullname" . }}-frontend
                port:
                  number: 80
{{- end }}
```

(The public shared *page* is `/s/{token}` — served by the frontend under the `/` rule. The backend share API is `/shared/{token}/*` — routed by the `/shared` rule. Distinct prefixes, no collision.)

- [ ] **Step 7: NOTES.txt** — copy `/root/git/linkhop/helm/linkhop/templates/NOTES.txt`, replace `linkhop`→`tidalwave`, and adjust any URL/credential hints to tidalwave's (Last.fm connect at `/auth/login`). Keep it short.

- [ ] **Step 8: Render the chart and verify it templates cleanly**

Run:
```bash
cd /root/git/tidalwave
helm lint helm/tidalwave
helm template tw helm/tidalwave \
  --set config.publicBaseUrl=https://tw.example.com \
  --set secrets.databaseUrl=postgresql+asyncpg://u:p@db:5432/tw \
  --set secrets.sessionSecret=xxx \
  --set ingress.host=tw.example.com | head -120
```
Expected: lint passes with 0 failures; `helm template` renders Deployments, Services, Secret, migration Job, poller CronJob, and the Ingress with `/auth`, `/stats`, `/shares`, `/shared` → backend and `/` → frontend. Verify the rendered Ingress actually contains those four backend paths.

- [ ] **Step 9: Commit**

```bash
cd /root/git/tidalwave
git add helm/tidalwave/templates/
git commit -m "feat: add Helm templates incl. poller CronJob + prefix-split Ingress"
```

---

## Task 5: GitHub Actions CI

**Files:**
- Create: `.github/workflows/backend.yml`, `.github/workflows/frontend.yml`, `.github/workflows/helm.yml`

**Interfaces:**
- Produces workflows mirroring linkhop's. They become active only once the repo is pushed to GitHub with a container registry configured — note this; they cannot be executed locally.

- [ ] **Step 1: Adapt the three workflows from linkhop**

Read `/root/git/linkhop/.github/workflows/{backend,frontend,helm}.yml`. Create the tidalwave equivalents with these adaptations:
- `backend.yml`: replace `linkhop`→`tidalwave`; the test job runs `uv sync` + `uv run pytest`; **add a Postgres service container** (image `postgres:16`, env `POSTGRES_USER/PASSWORD/DB=tidalwave`, ports 5432) because tidalwave's tests require a real Postgres (linkhop's may already do this — mirror it); the image build/push targets `ghcr.io/<owner>/tidalwave-backend`.
- `frontend.yml`: replace `linkhop`→`tidalwave`; build with pnpm + Node 22; image `ghcr.io/<owner>/tidalwave-frontend`. If linkhop's frontend workflow runs `pnpm gen:api` against `backend/openapi.json`, ensure `backend/openapi.json` is committed (it is, from the frontend plan) OR regenerate it in the workflow.
- `helm.yml`: replace `linkhop`→`tidalwave`; keep the `helm/chart-releaser-action` setup pointing at `helm/tidalwave`; image-tag handling mirrors linkhop's release flow.
- Match linkhop's trigger structure (push/tag patterns). Where linkhop tags releases `linkhop-<version>`, use `tidalwave-<version>`.

- [ ] **Step 2: Validate workflow YAML**

Run: `cd /root/git/tidalwave && (command -v actionlint >/dev/null && actionlint || python3 -c "import yaml,glob; [yaml.safe_load(open(f)) for f in glob.glob('.github/workflows/*.yml')]; print('workflow YAML parses')")`
Expected: `actionlint` clean if available, otherwise "workflow YAML parses" (valid YAML). Note in your report that the workflows only truly run once pushed to GitHub with `GITHUB_TOKEN`/registry permissions.

- [ ] **Step 3: Commit**

```bash
cd /root/git/tidalwave
git add .github/workflows/
git commit -m "ci: add backend, frontend, helm workflows"
```

---

## Task 6: Repo README + deploy docs

**Files:**
- Create: `README.md` (repo root)

- [ ] **Step 1: Write the root README**

Cover, concisely and accurately (read the code/specs, don't invent):
- What tidalwave is (multi-user Tidal listening tracker via Last.fm; one paragraph; link the design spec at `docs/superpowers/specs/2026-06-17-tidalwave-listening-tracker-design.md`).
- Architecture diagram (Tidal → Last.fm ← poller → Postgres → API ← SvelteKit), mirroring the spec.
- Local dev: backend (`cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn tidalwave.main:app --port 8080`, needs Postgres), frontend (`cd frontend && pnpm install && pnpm gen:api && pnpm dev`, needs Node 22 + pnpm).
- Deployment: `helm install tidalwave helm/tidalwave -n tidalwave --create-namespace` with required values (`config.publicBaseUrl`, `secrets.databaseUrl`, `secrets.lastfmApiKey`, `secrets.lastfmApiSecret`, `secrets.sessionSecret`, `ingress.host`). State that Postgres is external (CNPG) and the poller runs as a CronJob (`poller.schedule`).
- A note that the GitHub Actions workflows + chart-releaser need a GitHub remote + GHCR before they do anything.
- Link `backend/README.md` for the full backend env reference.

- [ ] **Step 2: Commit**

```bash
cd /root/git/tidalwave
git add README.md
git commit -m "docs: add repository README with deploy guide"
```

---

## Self-Review Notes (for the implementer)

- **Spec coverage:** delivers the spec's "same stack as linkhop, Helm chart, FluxCD/RKE2 target" deployment: Docker images (Tasks 1–2), Helm chart with backend/frontend/migration/Ingress/Secret (Tasks 3–4), plus the tidalwave-essential poller CronJob (Task 4, Step 5) without which no scrobbles are ingested. CI mirrors linkhop (Task 5).
- **Routing:** Ingress sends `/auth`, `/stats`, `/shares`, `/shared` to the backend and everything else (including the SPA's `/s/{token}` public page) to the frontend. This depends on the frontend plan having placed the public page at `/s/{token}` (not `/shared/{token}`).
- **Local validation limits:** Helm tasks are fully verifiable (`helm lint` + `helm template`). Docker builds and GitHub workflows cannot run in this environment — validate by review + path-existence + YAML parse, and rely on CI/a docker host for the real build. Call this out honestly in task reports; do not claim a docker image "builds" without having built it.
- **Prereqs from the frontend plan:** `frontend/pnpm-lock.yaml` and `backend/openapi.json` must exist (produced there) before the frontend image build and the `gen:api` CI step work.
- **Secrets:** `config.publicBaseUrl`, `secrets.databaseUrl`, `secrets.sessionSecret` are `required` in templates — `helm template`/`install` fails fast without them, which is intended.
