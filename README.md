# FastAPI Playground

A production-ready FastAPI application demonstrating modern Python development practices with Firebase integration. Built with Python 3.13+, this project showcases:

- **FastAPI** with async endpoints, automatic OpenAPI docs, and typed request/response models
- **Firebase Authentication** (ID token verification) + **Firestore** (user profile CRUD)
- **Firebase Cloud Functions** (Python 3.13 runtime, regional deployment, scaling controls)
- **Modern tooling**: `uv` for dependency management, `just` for task automation
- **Quality assurance**: Ruff (lint/format), ty (type checking), pytest (tests + coverage)
- **Production features**: Structured JSON logging, trace correlation, security headers, CORS, request size limits
- **CI/CD**: GitHub Actions with automated lint/type/test checks and coverage reporting

This README is optimized for AI code assistants: it documents actual module locations, environment variables, commands, architectural decisions, gotchas, and development patterns.

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
│   ├── helpers/                   # Test utility modules (auth, clients, profiles, starlette utils)
│   └── mocks/                     # Firebase / HTTP / service mocks
├── functions/                     # Firebase Cloud Functions (Python) codebase
│   ├── main.py                    # Example HTTPS callable (Hello world)
│   ├── requirements.txt           # Functions-specific deps (pin separately)
│   └── README.md                  # Deployment quickstart
├── .github/
│   ├── copilot-instructions.md    # Primary AI assistant guidelines
│   ├── instructions/              # Domain-specific instructions (openapi, tests)
│   ├── prompts/                   # Repo-specific prompt templates
│   ├── workflows/                 # CI + labeling automation
│   └── labeler.yml                # Auto-label configuration
├── pyproject.toml                 # Dependencies & tool configuration
├── uv.lock                        # Locked, reproducible dependency versions
├── Justfile                       # Task automation
├── Dockerfile                     # Multi-stage build (slim base by default)
├── .dockerignore                  # Docker build exclusions
├── .gitignore                     # Git exclusions
├── .env.example                   # Example environment configuration
├── firebase.json                  # Firebase project configuration
├── firestore.rules                # Firestore security rules
├── firestore.indexes.json         # Firestore index definitions
├── storage.rules                  # Cloud Storage security rules
├── GCP.md                         # Detailed GCP deployment & IAM guide
└── README.md                      # This file
```

## API Endpoints

### Root & Health
- `GET /` — Hello World + link to docs (returns `{ "message": "Hello World", "docs": "/api-docs" }`)
  - Not included in OpenAPI schema (`include_in_schema=False`)
- `GET /health` — Liveness probe (returns `{ "status": "healthy" }` with `Literal["healthy"]` type)
  - Lightweight probe for Cloud Run / K8s liveness checks
  - Tagged: `["health"]`
- `GET /api-docs` — Swagger UI (interactive API documentation)
- `GET /api-redoc` — ReDoc (alternative API documentation UI)

### Profile (Protected: `Authorization: Bearer <Firebase ID token>`)
- `POST /profile/` — Create profile (201 on success, 409 if exists, 422 on validation error)
- `GET /profile/` — Retrieve profile (200 on success, 404 if not found)
- `PUT /profile/` — Update profile (200 on success; partial updates via nullable/omitted fields)
- `DELETE /profile/` — Delete profile (200 on success, 404 if not found)

All profile endpoints return `ProfileResponse` with shape:
```json
{
  "success": true,
  "message": "Operation message",
  "profile": { /* Profile object or null */ }
}
```

### Profile Model (Response Shape)

```jsonc
{
   "firstname": "str",          // Required (1-100 chars)
   "lastname": "str",           // Required (1-100 chars)
   "email": "EmailStr",         // Required & validated
   "phone_number": "str",       // Required (E.164 format: +1234567890)
   "marketing": false,          // Boolean opt-in (default false)
   "terms": true,               // Must be true when creating
   "id": "<user uid>",          // Firebase user id (doc id, 1-128 chars)
   "created_at": "ISO-8601",    // Set at creation
   "updated_at": "ISO-8601"     // Updated on modification
}
```

## Prerequisites

- Python 3.13+
- `uv` (dependency & venv manager) — Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- `just` (task runner) — Install: `brew install just` (macOS) or see [just docs](https://github.com/casey/just)
- Firebase project (Authentication + Firestore enabled)
- Google Cloud project (optional for Cloud Run & trace/log context)

## Dependency Management

This project uses `uv` exclusively for dependency management (do not mix with pip/poetry):

- Dependencies declared in `pyproject.toml` (runtime + dev groups)
- Exact versions locked in `uv.lock` (~163KB) for reproducibility
- Virtual environment auto-created in `.venv/` on `uv sync`
- Use `just install` (alias for `uv sync`) to sync environment with lockfile
- Use `just update` (alias for `uv sync --upgrade`) to upgrade all dependencies

Adding a new dependency:
1. Add to `pyproject.toml` under `dependencies` or `[dependency-groups] dev`
2. Run `just install` to resolve and update `uv.lock`
3. Commit both `pyproject.toml` and `uv.lock`

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

Middleware stack (registration order in `app/main.py`):
1. `RequestContextLogMiddleware` — Adds trace context from `X-Cloud-Trace-Context` header
2. `BodySizeLimitMiddleware` — Enforces `MAX_REQUEST_SIZE_BYTES` limit (413 on exceed)
3. `SecurityHeadersMiddleware` — Adds security headers
4. `CORSMiddleware` — Handles CORS preflight/requests

Security headers added:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: same-origin`
- `Strict-Transport-Security` (HSTS) when HTTPS detected and not in debug mode (includes subdomains)

CORS:
- Deny-by-default (empty `allowed_origins` if `CORS_ORIGINS` unset or empty)
- Set `CORS_ORIGINS` to comma-separated list of explicit origins
- Credentials: `False`
- Methods: `GET, POST, PUT, DELETE, OPTIONS`
- Headers: `Authorization, Content-Type`

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
| Helpers | `tests/helpers/**` | Reusable test utilities (auth tokens, test clients, profile factories, Starlette utils) |
| Mocks | `tests/mocks/**` | Firebase Admin, HTTP, service mocks |

Test utilities:
- `tests/helpers/auth.py` — Generate mock Firebase tokens
- `tests/helpers/clients.py` — Build test clients with auth headers
- `tests/helpers/profiles.py` — Profile factory fixtures
- `tests/helpers/starlette_utils.py` — Starlette request/response helpers
- `tests/mocks/firebase.py` — Mock Firebase Admin SDK
- `tests/mocks/http.py` — Mock HTTP responses
- `tests/mocks/services.py` — Mock service layer

Examples:
```bash
just test
just test tests/unit/models/test_profile_models.py
just test tests/integration/test_api.py::test_health
just cov
```
Notes: Firebase/Firestore interactions patched via `conftest.py`; no real network calls.

## Error Responses

Standard business error shape (`ErrorResponse` from `app/models/error.py`):
```json
{ "detail": "<message>" }
```
Examples: `{"detail": "Unauthorized"}`, `{"detail": "Profile not found"}`, `{"detail": "Profile already exists for this user"}`

Validation errors keep FastAPI default list form with field-specific details.

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

Emulator ports (from `firebase.json`):
- Auth: 7010
- Functions: 7020
- Firestore: 7030
- Storage: 7040
- UI: auto-assigned (enabled)
- `singleProjectMode: true` (simplified multi-service setup)

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
## Configuration Files Reference

| File | Purpose |
| ---- | ------- |
| `.env` | Local environment variables (gitignored; copy from `.env.example`) |
| `.env.example` | Example environment configuration template |
| `firebase.json` | Firebase project config (Functions, Firestore, Storage, Emulator ports) |
| `firestore.rules` | Firestore security rules |
| `firestore.indexes.json` | Firestore composite index definitions |
| `storage.rules` | Cloud Storage security rules |
| `.firebaserc` | Firebase project aliases (gitignored if contains real project IDs) |
| `.dockerignore` | Files excluded from Docker builds |
| `.editorconfig` | Editor formatting consistency (indent, line endings, charset) |
| `.python-version` | Python version hint for version managers |
| `pyproject.toml` | Python dependencies, tool configs (Ruff, ty, pytest, coverage) |
| `uv.lock` | Locked dependency versions for reproducibility |

## Infrastructure Docs

Extended Google Cloud & Firebase provisioning guide lives in [`GCP.md`](GCP.md). Keep README high-level; update `GCP.md` for infra changes (regions, IAM roles, API enablement, CI/CD specifics).

---
## CI & Automation

### Workflow `.github/workflows/ci.yml`
Triggers: Push to `main`, PRs to `main`

Steps:
1. Checkout code
2. Set up Python 3.13
3. Set up uv (Astral's package manager)
4. Set up just (task runner)
5. Install dependencies (`just install`)
6. Run lint checks (`just lint`) — Ruff check + format
7. Run typing checks (`just typing`) — ty static analysis
8. Run test coverage (`just cov`) — pytest with coverage
9. Upload coverage artifact (htmlcov/)
10. Post coverage comment on PR (via `dima-engineer/pytest-reporter@v4`)

Permissions:
- `contents: read`
- `pull-requests: write` (for coverage comments)

Concurrency: Cancel in-progress runs for same ref

Coverage thresholds:
- Currently commented out (`cov-threshold-single: 85`, `cov-threshold-total: 90`)
- Omit `tests/*` from coverage percentage calculation
- Async tests supported

### Label Automation
- `.github/workflows/labeler.yml` — Auto-labels PRs based on changed paths
- `.github/workflows/labeler-manual.yml` — Manual dispatch for backfilling labels (params: `maxCount`, `scope`)
- `.github/labeler.yml` — Label rules configuration

## Development Conventions

### Code Style
- Routers thin; put logic in `services/`.
- Async endpoints; document if using sync I/O.
- Type hints everywhere (Ruff `ANN` rules enforced).
- Group imports: stdlib / third-party / local with blank line separators.
- Access config only via `get_settings()` (never direct `os.getenv`).
- No direct env reads or secret logging.
- Pydantic models use `extra="forbid"` to catch typos/unexpected fields.
- Use structured logging with `extra={...}` for context (never log PII/secrets).
- Line length: 120 chars (Ruff config).
- Use `from __future__ import annotations` for forward references.

### File Naming
- Python modules: `snake_case.py`
- Test files: `test_<module_name>.py` (mirrors source structure where practical)
- Models: Named after domain concept (e.g., `profile.py`, `health.py`, `error.py`)
- Routers: Named after resource (e.g., `profile.py` for `/profile` endpoints)
- Services: Named after domain (e.g., `profile.py` for profile business logic)

### Test Organization
- Unit tests: `tests/unit/<app_path>/test_<module>.py` (mirrors app structure)
- Integration tests: `tests/integration/test_<feature>.py`
- E2E tests: `tests/e2e/test_<scenario>.py`
- Test helpers: `tests/helpers/<helper_name>.py` (reusable utilities)
- Mocks: `tests/mocks/<service_name>.py` (fake implementations)

## Gotchas & Recommendations

| Area | Detail | Recommendation |
| ---- | ------ | -------------- |
| Firestore sync calls | Blocking inside async endpoints | Wrap in `anyio.to_thread.run_sync` if performance degrades |
| Unused deps | `httpx`, `python-jose` not imported | Remove unless near-term use planned to reduce supply-chain surface |
| Secret Manager flag | `SECRET_MANAGER_ENABLED` exists but unused | Implement secret loading logic or remove setting |
| Optional env vars | `APP_ENVIRONMENT`, `APP_URL`, `FIREBASE_PROJECT_NUMBER` | Only set if needed for logging context / external references |
| CORS default | Empty `CORS_ORIGINS` denies all | Always set explicit origins for browser clients; backend-to-backend doesn't need it |
| Large bodies | Hard 413 at `MAX_REQUEST_SIZE_BYTES` limit | Communicate size limits to clients; no buffering occurs (streams + early abort) |
| Profile collection name | Hardcoded as `"profiles"` in `app/models/profile.py` | Change constant + tests if rename needed; not configurable via env |
| Auth dependency pattern | `_current_user_dependency` wrapper in router | Enables test patching; don't inline `verify_firebase_token` directly |
| HSTS behavior | Only activates on HTTPS + non-debug | Local dev (HTTP) won't see HSTS header; expected behavior |
| Test isolation | All Firebase/Firestore calls mocked | Never runs real network calls; use emulator for integration testing if needed |
| Middleware order matters | Logging → Body Limit → Security → CORS | Don't reorder without understanding request flow impact |
| Model validation | `extra="forbid"` on all request models | Typos/unknown fields rejected with 422; intentional strictness |

## For AI Assistants

### Adding an endpoint:
1. Define request/response models in `app/models/` (use `BaseModel`, add field validation, set `extra="forbid"`).
2. Implement service logic in `app/services/` (use async if I/O-bound; inject Firestore via `get_firestore_client()`).
3. Create router in `app/routers/` using `APIRouter` with tags, status codes, `responses` dict for error cases.
4. Register router in `app/main.py` with `app.include_router(router, prefix="/path", tags=["tag"])`.
5. Add tests: unit (service), integration (route + auth), e2e (flow if multi-step).
6. Update `.github/instructions/openapi.instructions.md` if endpoint has special OpenAPI requirements.

### Adding config:
1. Add field in `Settings` (`app/core/config.py`) with Field, type hint, and env alias.
2. Access via `get_settings()` in functions (never `os.getenv`).
3. Update README environment table if user-facing.
4. Update `.env.example` with sample value.

### Adding middleware:
1. Create middleware in `app/core/` (extend Starlette `BaseHTTPMiddleware` or use plain ASGI).
2. Register in `app/main.py` via `app.add_middleware()` in correct order (logging first, then body limit, then security, then CORS last).
3. Add integration tests in `tests/integration/`.

### Key files for context:
- `app/main.py` — App factory, middleware registration, root endpoints
- `app/core/config.py` — All environment-driven settings
- `app/models/profile.py` — Profile domain models + `PROFILE_COLLECTION` constant
- `tests/conftest.py` — Test fixtures, Firebase/Firestore mocking patterns
- `tests/helpers/` — Reusable test utilities (auth token generation, client builders, profile factories)

## Quick Reference Card

### Most Common Commands
```bash
just serve              # Start dev server (http://127.0.0.1:8080)
just test               # Run all tests
just cov                # Run tests with coverage report
just lint               # Lint and format code
just typing             # Type check
just check-all          # Run all QA checks
just install            # Sync dependencies
```

### Key Files to Modify
| Task | File(s) to Change |
| ---- | ----------------- |
| Add endpoint | `app/routers/<resource>.py`, `app/models/<resource>.py`, `app/services/<resource>.py`, register in `app/main.py` |
| Add env var | `app/core/config.py` (Settings class), `.env.example`, README env table |
| Add middleware | `app/core/<middleware>.py`, register in `app/main.py` |
| Add dependency | `pyproject.toml`, run `just install`, commit `uv.lock` |
| Configure Firebase | `firebase.json`, `firestore.rules`, `firestore.indexes.json` |
| Add Cloud Function | `functions/main.py`, optionally update `functions/requirements.txt` |

### Common Imports Pattern
```python
# Stdlib
import logging
from datetime import UTC, datetime
from typing import Annotated

# Third-party
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

# Local
from app.core.config import get_settings
from app.core.firebase import get_firestore_client
from app.models.profile import Profile, ProfileCreate
```

### Environment Variables Quick List
Required: `FIREBASE_PROJECT_ID`  
Important: `CORS_ORIGINS` (if browser clients), `GOOGLE_APPLICATION_CREDENTIALS` (local dev)  
Optional: `DEBUG`, `ENVIRONMENT`, `PORT`, `MAX_REQUEST_SIZE_BYTES`  
Informational: `APP_ENVIRONMENT`, `APP_URL`, `FIREBASE_PROJECT_NUMBER`

## License

MIT License – see [`LICENSE`](LICENSE).
