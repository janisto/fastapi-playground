# FastAPI Playground

A small FastAPI app showcasing Cloud Functions, Firebase Authentication, Firestore CRUD, typed Pydantic models, and a tidy development workflow with `uv` (dependency & virtualenv manager) and `just` (task runner). This README is optimized for AI code assistants: it lists actual module locations, environment variables, commands, architectural decisions, and gotchas.

## Features

- FastAPI (Python 3.13+) with async endpoints and automatic OpenAPI docs (`/api-docs`, `/api-redoc`)
- Firebase Authentication (ID token verification via Admin SDK)
- Firestore persistence for user profile documents
- Firebase Cloud Functions (Python 3.13 runtime) example (`functions/main.py`) with regional config & scaling limits
- Structured one-line JSON logging (Cloud Run friendly, trace correlation via `X-Cloud-Trace-Context` header)
- Pydantic v2 models + `pydantic-settings` for env-driven configuration
- Custom middlewares: security headers, request body size limiting, request-context logging
- Strict CORS allowlist (deny-by-default)
- Tests (unit, integration, e2e happy paths) via `pytest` / `pytest-asyncio` with coverage reports
- Linting + formatting + modernization via Ruff (`check` + `format` + `UP` rules)
- Static typing checks via `ty`
- Reproducible, minimal container build with optional base image auto-updates for Cloud Run

## Project Structure

```
├── app/
│   ├── main.py                    # FastAPI application factory + lifespan
│   ├── dependencies.py            # (Currently minimal) shared dependency wiring
│   ├── auth/
│   │   └── firebase.py            # Token verification + security scheme
│   ├── core/
│   │   ├── config.py              # Settings (env -> Settings class)
│   │   ├── firebase.py            # Firebase Admin & Firestore init/helpers
│   │   ├── logging.py             # JSON logging + request trace middleware
│   │   ├── security.py            # Security headers middleware
│   │   └── body_limit.py          # Request size guard middleware
│   ├── models/
│   │   ├── error.py               # Canonical error response shape
│   │   ├── health.py              # Health probe model
│   │   └── profile.py             # Profile domain models (create/update/response)
│   ├── routers/
│   │   └── profile.py             # CRUD endpoints (protected by Firebase Auth)
│   └── services/
│       └── profile.py             # Firestore-backed profile service
├── tests/
│   ├── conftest.py                # Fixtures / patching
│   ├── unit/                      # Fine-grained model/auth/core tests
│   ├── integration/               # API + middleware behavior tests
│   ├── e2e/                       # Happy path scenario(s)
│   ├── helpers/                   # Test utility modules
│   └── mocks/                     # Firebase / HTTP mocks
├── functions/                     # Firebase Cloud Functions (Python) codebase
│   ├── main.py                    # Example HTTPS callable (Hello world)
│   ├── requirements.txt           # Functions-specific deps (pin separately)
│   └── README.md                  # Deployment quickstart
├── .github/
│   ├── workflows/                 # CI + labeling automation
│   ├── instructions/              # Copilot / contributor guidance
│   └── prompts/                   # Repo-specific prompt templates
├── pyproject.toml                 # Dependencies & tool configuration
├── uv.lock                        # Locked, reproducible dependency versions
├── Justfile                       # Task automation
├── Dockerfile                     # Multi-stage build (slim base by default)
└── README.md
```

## API Endpoints

### Root & Health
- `GET /` — Hello World + link to docs
- `GET /health` — Liveness probe (returns `{ "status": "healthy" }`)
- `GET /api-docs` — Swagger UI
- `GET /api-redoc` — ReDoc

### Profile (Protected: `Authorization: Bearer <Firebase ID token>`)
- `POST /profile/` — Create profile
- `GET /profile/` — Retrieve profile
- `PUT /profile/` — Update profile (partial via nullable/omitted fields)
- `DELETE /profile/` — Delete profile

### Profile Model (Response Shape)

```jsonc
{
   "firstname": "str",          // Required
   "lastname": "str",           // Required
   "email": "EmailStr",         // Required & validated
   "phone_number": "str",       // Required
   "marketing": false,           // Boolean opt-in (default false)
   "terms": true,                // Must be true when creating
   "id": "<user uid>",          // Firebase user id (doc id)
   "created_at": "ISO-8601",    // Set at creation
   "updated_at": "ISO-8601"     // Updated on modification
}
```

## Prerequisites

- Python 3.13+
- `uv` (dependency & venv manager)
- `just` (task runner)
- Firebase project (Authentication + Firestore enabled)
- Google Cloud project (optional for Cloud Run & trace/log context)

## Tech Stack & Dependencies

Runtime (`pyproject.toml`):
- `fastapi[standard]` (serving, schema, docs)
- `uvicorn[standard]` (ASGI server; `fastapi dev` used for hot reload in dev)
- `firebase-admin` (Auth token verification + Firestore client)
- `pydantic`, `pydantic-settings` (validation & configuration)
- `httpx` (currently unused; available for outbound HTTP if needed)
- `python-jose[cryptography]` (currently unused; consider removal unless future JWT parsing sans Firebase Admin is planned)

Dev / QA:
- `pytest`, `pytest-asyncio`, `pytest-cov`, `pytest-httpx`
- `ruff` (lint, format, modernization via `UP` rules)
- `ty` (static typing / inference checks)

Unused packages (as of analysis): `python-jose`, `httpx` are not imported anywhere. Prune to reduce supply-chain surface unless slated for upcoming features.

## Environment Configuration

Loaded automatically from `.env` (see `config.Settings`).

| Env Var | Required | Default | Purpose |
| ------- | -------- | ------- | ------- |
| `ENVIRONMENT` | No | `production` | Environment label (affects logging posture & HSTS) |
| `DEBUG` | No | `True` | Enable debug behaviors (verbosity, reload) |
| `HOST` | No | `0.0.0.0` | Bind address |
| `PORT` | No | `8080` | Listen port (Cloud Run uses this) |
| `FIREBASE_PROJECT_ID` | Yes* | `test-project` | Firebase / GCP project id (Auth, Firestore, trace correlation) |
| `FIREBASE_PROJECT_NUMBER` | No | `None` | Numeric project number (future integrations / logging metadata) |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | `None` | Path to service account JSON (local dev only; omit in Cloud Run) |
| `APP_ENVIRONMENT` | No | `None` | Optional secondary environment label (surfaced in logs if set) |
| `APP_URL` | No | `None` | Public application URL (informational) |
| `SECRET_MANAGER_ENABLED` | No | `True` | Placeholder flag (no logic yet) |
| `MAX_REQUEST_SIZE_BYTES` | No | `1000000` | Request body limit (bytes) |
| `CORS_ORIGINS` | No | (empty) | Comma-separated allowed origins (deny all if unset) |

(*Provide real values outside tests.)

Firestore profile collection name is fixed to `profiles` (see `app/models/profile.py`) and no longer configurable via env var.

Example `.env` (minimal + optional extras commented):
```env
ENVIRONMENT=development
DEBUG=true
FIREBASE_PROJECT_ID=my-firebase
MAX_REQUEST_SIZE_BYTES=1000000
CORS_ORIGINS=https://example.com,https://app.example.com
# Optional extras:
# FIREBASE_PROJECT_NUMBER=123456789012
# APP_ENVIRONMENT=dev
# APP_URL=http://127.0.0.1:8080
```

## Quick Start

```bash
git clone <repository-url>
cd fastapi-playground
just install
just serve       # http://127.0.0.1:8080/api-docs
```

## Commands (Justfile)

```bash
just                # List tasks

# Dev
just serve          # Dev server (fastapi dev)
just browser        # Open browser
just req health     # httpie helper via uvx

# Quality
just lint           # Ruff check + format
just modernize      # Ruff upgrade rules
just typing         # Type checking (ty)
just test           # Pytest
just cov            # Pytest w/ coverage html/json
just check-all      # lint + typing + test

# Lifecycle
just install        # uv sync
just update         # uv sync --upgrade
just clean          # Remove caches/venv/coverage
just fresh          # clean + install

# Containers
just docker-build   # Build image (python:3.13-slim*)
just docker-run     # Run with env-file + port
just docker-logs    # Tail logs
```

Direct equivalents:
```bash
uv sync
uv run -m pytest
uvx ruff check && uvx ruff format
docker build -t fastapi-playground:local .
docker run --rm -p 8080:8080 --env-file .env fastapi-playground:local
```

## Development Workflow

1. Implement feature (routers thin; logic in `services/`).
2. Add/adjust Pydantic models in `app/models/`.
3. Write/extend tests (unit → service/model; integration → API; e2e for flow).
4. Run `just lint && just typing`.
5. Run targeted tests (`just test tests/integration/test_api.py::test_health`).
6. Run `just cov` before PR.
7. Commit using Conventional Commit style.

## CORS & Security Headers

- CORS deny-by-default. Set `CORS_ORIGINS` to explicit origins.
- Middleware adds: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`; HSTS when HTTPS & not debug.

## Request Size Limits

`BodySizeLimitMiddleware` aborts with `413` if body exceeds `MAX_REQUEST_SIZE_BYTES` without buffering the entire body (streams & early abort: pre-checks `Content-Length`, then counts chunks incrementally).

## Logging & Trace Correlation

JSON logs (`app/core/logging.py`): keys include `severity`, `message`, `time`, `logger`, source location, optional `trace` / `spanId` derived from `X-Cloud-Trace-Context` (Cloud Run / GCP). Extra structured fields passed via `extra={...}` (excluding reserved attributes) are merged; `None` values serialized as the string `"null"` to ensure consistent key presence.

Usage example:
```python
logger.info("profile created", extra={"user_id": uid, "profile_id": uid})
```

## Authentication Flow

Client obtains Firebase ID token → send header:
```
Authorization: Bearer <id_token>
```
Failure cases:
- Missing header → 403 (security scheme)
- Invalid/expired token → 401 `{ "detail": "Unauthorized" }`

## Firestore Service Notes

`ProfileService` uses synchronous Firestore client in async endpoints (acceptable for low concurrency). Consider offloading with `anyio.to_thread.run_sync` or adopting async abstractions for heavier loads.

## Testing

| Category | Path | Focus |
| -------- | ---- | ----- |
| Unit | `tests/unit/**` | Models, config, small pure logic |
| Integration | `tests/integration/**` | API routes, middleware |
| E2E | `tests/e2e/**` | High-level flows |

Examples:
```bash
just test
just test tests/unit/models/test_profile_models.py
just test tests/integration/test_api.py::test_health
just cov
```
Notes: Firebase/Firestore interactions patched; no real network calls.

## Error Responses

Standard business error shape (`ErrorResponse`):
```json
{ "detail": "<message>" }
```
Validation errors keep FastAPI default list form.

## Example Requests

Create a profile:
```bash
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"firstname":"John","lastname":"Doe","email":"john@example.com","phone_number":"+1234567890","terms":true}' \
  http://localhost:8080/profile/
```

## Container Usage (Local)

```bash
just docker-build
just docker-run

# Or manual
docker build -t fastapi-playground:local .
docker run --rm -p 8080:8080 --env-file .env fastapi-playground:local
```
Override base image:
```bash
just docker-build pyimg=python:3.13-slim-bookworm
```

## Deployment (Cloud Run)

```bash
docker build -t gcr.io/PROJECT_ID/fastapi-playground .
docker push gcr.io/PROJECT_ID/fastapi-playground
gcloud run deploy fastapi-playground \
  --image gcr.io/PROJECT_ID/fastapi-playground \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```
For a detailed, end-to-end infrastructure and IAM setup (APIs, roles, environment variables, Cloud Build integration, Functions vs Cloud Run guidance) see: [`GCP.md`](GCP.md).

Automatic base updates:
```bash
gcloud run deploy fastapi-playground \
  --image gcr.io/PROJECT_ID/fastapi-playground:TAG \
  --base-image python:3.13-slim \
  --automatic-updates
```
Production env vars:
```text
ENVIRONMENT=production
DEBUG=false
FIREBASE_PROJECT_ID=<real>
```

## Firebase Cloud Functions (Python)

This repo also includes a minimal Firebase Cloud Functions (2nd gen) Python codebase under `functions/`, showcasing how to deploy auxiliary HTTP endpoints alongside (or instead of) the FastAPI service.

Key points:

- Runtime: Python 3.13 (`"runtime": "python313"` in `firebase.json`).
- Region: `europe-west4` (set globally via `options.set_global_options`).
- Memory: 128 MB (`memory=options.MemoryOption.MB_128`).
- Scaling limits (env-configurable):
  - `MIN_INSTANCES` (default 0)
  - `MAX_INSTANCES` (default 2)
- Example function: `on_request_example` returns a simple "Hello world!" response.
- Dependencies isolated in `functions/requirements.txt` (keep aligned with top-level deps where overlap exists, but pin separately to control cold start variance).

### Project Config (firebase.json excerpt)

```jsonc
{
  "functions": [
    {
      "source": "functions",
      "location": "europe-west4",
      "codebase": "default",
      "runtime": "python313"
    }
  ],
  "emulators": {
    "auth": { "port": 7010 },
    "functions": { "port": 7020 },
    "firestore": { "port": 7030 },
    "storage": { "port": 7040 },
    "ui": { "enabled": true },
    "singleProjectMode": true
  }
}
```

### Deployment

From repository root (or `cd functions` first):

```bash
python3 -m venv venv                # (Optional: isolate build env for dependency resolution)
source venv/bin/activate
pip install -r functions/requirements.txt
export FUNCTIONS_DISCOVERY_TIMEOUT=30  # Helps CLI module scan (avoid premature timeout)
firebase deploy --only functions
deactivate
```

Common one-liner (already have an active virtualenv):
```bash
pip install -r functions/requirements.txt && firebase deploy --only functions
```

Set scaling overrides per deployment (bash examples):
```bash
export MIN_INSTANCES=0
export MAX_INSTANCES=3
firebase deploy --only functions
```

### Emulator Suite

Run local emulators (functions + auth + firestore + storage) with ports defined in `firebase.json`:
```bash
firebase emulators:start
```
Or just functions:
```bash
firebase emulators:start --only functions
```
Access the Emulator UI (auto-listed in terminal) to inspect requests, Firestore docs, and Auth users.

Environment parity tips:
- Provide service account credentials if your function code escalates privileges beyond emulator defaults (`GOOGLE_APPLICATION_CREDENTIALS`).
- Ensure any additional env vars (e.g., `MIN_INSTANCES`, `MAX_INSTANCES`) are exported before starting the emulator for realistic behavior.

### When to Use Functions vs FastAPI

| Use Case | Prefer FastAPI App | Prefer Cloud Function |
| -------- | ------------------ | --------------------- |
| Many cohesive REST endpoints | ✅ | ❌ |
| Single lightweight webhook / trigger | ❌ | ✅ |
| Needs custom middleware stack, complex routing | ✅ | ❌ |
| Sporadic traffic, pay-per-invoke desirable | ⚠️ (cold starts if Cloud Run min=0) | ✅ |
| Long-lived connections / streaming | ✅ | ❌ (not ideal) |

You can mix both: keep core API in FastAPI (Cloud Run) and deploy isolated experimental or region-specific endpoints as Functions.

### Adding More Functions

1. Create a new function in `functions/main.py` using `@https_fn.on_request()` or other trigger decorators.
2. (Optional) Add per-function `max_instances` or `timeout_sec` in the decorator parameters.
3. Update tests (if you add business logic—consider factoring non-trigger code into reusable modules for unit testing outside the Firebase runtime).
4. Redeploy: `firebase deploy --only functions`.

### Vertex AI / Generative AI (Optional)

The scaffold includes commented guidance for Vertex AI via `google-genai`. To enable:
1. Uncomment and initialize a `genai.Client` with `project` & `location`.
2. Add required permissions (service account) for Vertex AI endpoints.
3. Keep memory/timeout sizing in mind for model invocation latency.

---
## Infrastructure Docs

Extended Google Cloud & Firebase provisioning guide lives in [`GCP.md`](GCP.md). Keep README high-level; update `GCP.md` for infra changes (regions, IAM roles, API enablement, CI/CD specifics).

---
## CI & Automation

Workflow `.github/workflows/ci.yml`:
1. Install (uv)
2. Lint (ruff)
3. Typing (ty)
4. Coverage tests (pytest + htmlcov artifact)
5. Coverage comment on PRs (threshold currently not enforced)

Label automation:
- Auto: `.github/workflows/labeler.yml`
- Manual backfill: `.github/workflows/labeler-manual.yml` (dispatch with `maxCount`, `scope`)

## Development Conventions

- Routers thin; put logic in `services/`.
- Async endpoints; document if using sync I/O.
- Type hints everywhere (Ruff `ANN` rules).
- Group imports: stdlib / third-party / local.
- Access config only via `get_settings()`.
- No direct env reads or secret logging.
- Tests: prefer deterministic, isolated units.

## Gotchas & Recommendations

| Area | Detail | Recommendation |
| ---- | ------ | -------------- |
| Firestore sync calls | Blocking inside async | Wrap in thread executor if performance degrades |
| Unused deps | `httpx`, `python-jose` | Remove unless near-term use planned |
| Secret Manager flag | Unused setting | Implement or drop to reduce confusion |
| Additional env vars (APP_ENVIRONMENT, APP_URL, FIREBASE_PROJECT_NUMBER) | Optional metadata | Only set if needed for logging / external references |
| CORS default | Empty denies all | Always set for browser clients |
| Large bodies | Hard 413 at limit | Communicate to clients uploading large JSON |

## For AI Assistants

Adding an endpoint:
1. Define request/response models (`app/models/`).
2. Implement service logic (`app/services/`).
3. Create router (`app/routers/`) using `APIRouter` with tags.
4. Register router in `app/main.py`.
5. Add tests: unit (service), integration (route), e2e (flow if needed).

Adding config:
1. Add field in `Settings` with env alias.
2. Access via `get_settings()` in functions.
3. Update README if externally relevant.

## License

MIT License – see [`LICENSE`](LICENSE).
