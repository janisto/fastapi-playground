# FastAPI Playground

A FastAPI application demonstrating Firebase Authentication, Firestore CRUD operations, typed Pydantic v2 models, and a modern Python development workflow using `uv` (dependency & virtualenv manager) and `just` (task runner). This README is optimized for AI code assistants.

<img src="assets/python.svg" alt="Python logo" width="400">

<sub>Python logo from [python.org](https://www.python.org/community/logos/). Trademark of the Python Software Foundation.</sub>

## Features

- **FastAPI** (Python 3.14+) with async endpoints and OpenAPI docs (`/api-docs`, `/api-redoc`)
- **Firebase Authentication** (ID token verification via Admin SDK with revocation checks)
- **Firestore persistence** for user profile documents with async transactional operations
- **Firebase Cloud Functions** (Python 3.14 runtime) example with regional config & scaling limits
- **Structured JSON logging** (Cloud Run compatible, trace correlation via `X-Cloud-Trace-Context`)
- **Pydantic v2** models + `pydantic-settings` for type-safe configuration
- **Custom middlewares**: security headers, request body size limiting, request-context logging
- **Domain exceptions** with HTTP semantics for clean error handling
- **Strict CORS** allowlist (deny-by-default)
- **Tests** (unit, integration, E2E) via `pytest` / `pytest-asyncio` with coverage reports
- **Linting + formatting** via Ruff (`check` + `format` + comprehensive rules)
- **Static typing** via `ty`
- **Container build** with multi-stage Dockerfile for Cloud Run deployment

## Project Structure

```
├── app/
│   ├── main.py                    # FastAPI app factory + lifespan manager
│   ├── dependencies.py            # Dependency injection (CurrentUser, ProfileServiceDep)
│   ├── auth/
│   │   └── firebase.py            # Token verification + FirebaseUser dataclass
│   ├── core/
│   │   ├── config.py              # Settings class (pydantic-settings)
│   │   ├── firebase.py            # Firebase Admin SDK & async Firestore client
│   │   └── handlers/              # Exception handlers (domain, http, validation)
│   ├── exceptions/
│   │   ├── __init__.py            # Exports all domain exceptions
│   │   ├── base.py                # DomainError, NotFoundError, ConflictError
│   │   └── profile.py             # ProfileNotFoundError, ProfileAlreadyExistsError
│   ├── middleware/
│   │   ├── __init__.py            # Exports middleware and logging utilities
│   │   ├── body_limit.py          # Request size guard (413 on oversized)
│   │   ├── logging.py             # JSON logging + audit events + trace context
│   │   └── security.py            # Security headers (HSTS, X-Frame-Options, etc.)
│   ├── models/
│   │   ├── error.py               # ErrorResponse schema
│   │   ├── health.py              # HealthResponse schema
│   │   ├── profile.py             # Profile domain models + PROFILE_COLLECTION
│   │   └── types.py               # Shared type aliases (NormalizedEmail, Phone, etc.)
│   ├── routers/
│   │   ├── health.py              # Health check endpoint
│   │   └── profile.py             # Profile CRUD (Firebase Auth protected)
│   └── services/
│       └── profile.py             # ProfileService with async Firestore transactions
├── tests/
│   ├── conftest.py                # Root fixtures (client, fake_user, with_fake_user)
│   ├── helpers/                   # Test utilities (auth helpers, factories)
│   ├── mocks/                     # Firebase / HTTP mocks
│   ├── unit/                      # Unit tests (mirrors app/ structure)
│   ├── integration/               # API route tests (mirrors app/routers/)
│   └── e2e/                       # Firebase emulator tests (local only)
├── functions/                     # Firebase Cloud Functions (Python 3.14)
│   ├── main.py                    # Example HTTPS callable
│   └── pyproject.toml             # Functions-specific dependencies
├── .github/
│   ├── workflows/                 # CI (lint, typing, tests, coverage)
│   ├── agents/                    # Copilot agent configurations
│   └── skills/                    # Copilot skill definitions
├── pyproject.toml                 # Dependencies & tool config (Ruff, ty, pytest)
├── uv.lock                        # Locked dependency versions
├── Justfile                       # Task automation
├── Dockerfile                     # Multi-stage container build
└── README.md
```

## API Endpoints

### Root & Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Root endpoint (returns hello + docs link) |
| `GET` | `/health/` | Liveness probe (`{"status": "healthy"}`) |
| `GET` | `/api-docs` | Swagger UI |
| `GET` | `/api-redoc` | ReDoc |

### Profile (Protected: `Authorization: Bearer <Firebase ID token>`)

| Method | Path | Description | Success | Errors |
|--------|------|-------------|---------|--------|
| `POST` | `/profile/` | Create profile | 201 | 401, 403, 409, 500 |
| `GET` | `/profile/` | Get profile | 200 | 401, 404, 500 |
| `PATCH` | `/profile/` | Partial update profile | 200 | 401, 404, 500 |
| `DELETE` | `/profile/` | Delete profile | 200 | 401, 404, 500 |

### Profile Model (Response Shape)

```jsonc
{
  "success": true,
  "message": "Profile created successfully",
  "profile": {
    "id": "<user uid>",           // Firebase UID (document ID)
    "firstname": "John",          // Required, 1-100 chars
    "lastname": "Doe",            // Required, 1-100 chars
    "email": "user@example.com",  // Required, auto-lowercased
    "phone_number": "+358401234567", // E.164 format
    "marketing": false,           // Boolean opt-in
    "terms": true,                // Must be true when creating
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

## Prerequisites

- **Python 3.14+**
- **uv** (dependency & venv manager) — `brew install uv` or `pip install uv`
- **just** (task runner) — `brew install just`
- **libmagic** (for python-magic file type detection) — `brew install libmagic`
- **Firebase project** (Authentication + Firestore enabled)
- **Google Cloud project** (optional, for Cloud Run & trace correlation)

## Tech Stack

### Runtime Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi[standard]` | Web framework with Swagger/ReDoc |
| `uvicorn[standard]` | ASGI server (used via `fastapi dev` for hot reload) |
| `firebase-admin` | Auth token verification + async Firestore client |
| `pydantic` | Data validation and serialization |
| `pydantic-settings` | Environment-based configuration |
| `httpx` | HTTP client (used in tests with pytest-httpx) |
| `python-magic` | File type detection |

### Dev Dependencies

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-asyncio` | Async test support (`asyncio_mode = "auto"`) |
| `pytest-cov` | Coverage reporting |
| `pytest-httpx` | HTTP mocking for outbound requests |
| `pytest-mock` | Mocking via `mocker` fixture |
| `ruff` | Linting + formatting (line-length 120) |
| `ty` | Static type checking |

## Environment Configuration

Loaded from `.env` via `pydantic-settings` (see [app/core/config.py](app/core/config.py)).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `production` | Environment label (affects logging, HSTS) |
| `DEBUG` | No | `False` | Debug mode (verbosity, reload) |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8080` | Listen port (Cloud Run uses this) |
| `FIREBASE_PROJECT_ID` | Yes* | `test-project` | Firebase/GCP project ID |
| `FIREBASE_PROJECT_NUMBER` | No | `None` | Numeric project number (logging metadata) |
| `FIRESTORE_DATABASE` | No | `None` | Firestore database ID (defaults to `(default)`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | `None` | Path to service account JSON (local dev only) |
| `APP_ENVIRONMENT` | No | `None` | Optional environment label for logs |
| `APP_URL` | No | `None` | Public application URL (informational) |
| `SECRET_MANAGER_ENABLED` | No | `True` | Placeholder for Secret Manager integration |
| `MAX_REQUEST_SIZE_BYTES` | No | `1000000` | Request body size limit (bytes) |
| `CORS_ORIGINS` | No | (empty) | Comma-separated allowed origins |

*Provide real values outside tests. The Firestore collection name is fixed to `profiles` (see [app/models/profile.py](app/models/profile.py)).

**Example `.env`:**
```env
ENVIRONMENT=development
DEBUG=true
FIREBASE_PROJECT_ID=my-firebase-project
MAX_REQUEST_SIZE_BYTES=1000000
CORS_ORIGINS=https://example.com,https://app.example.com
```

## Quick Start

```bash
git clone <repository-url>
cd fastapi-playground
just install        # Install dependencies via uv
just serve          # Start dev server at http://127.0.0.1:8080
```

Open http://127.0.0.1:8080/api-docs for Swagger UI.

## Commands (Justfile)

### Development

| Command | Description |
|---------|-------------|
| `just serve` | Start dev server (`fastapi dev` with hot reload) |
| `just browser` | Open dev server in browser |
| `just req <path>` | HTTP request via httpie (`just req health/`) |
| `just emulators` | Start Firebase emulators (auth + firestore) for E2E tests |

### Quality Assurance

| Command | Description |
|---------|-------------|
| `just lint` | Run Ruff check + format |
| `just typing` | Type checking via ty |
| `just test` | Unit + integration tests (CI-compatible) |
| `just test-unit` | Unit tests only |
| `just test-integration` | Integration tests only |
| `just test-e2e` | E2E tests (requires `just emulators`) |
| `just test-all` | All tests including E2E |
| `just cov` | Run tests with coverage (html/json reports) |
| `just check-all` | lint + typing + test |
| `just modernize` | Apply Ruff pyupgrade rules |

### Lifecycle

| Command | Description |
|---------|-------------|
| `just install` | Sync dependencies (`uv sync`) |
| `just update` | Upgrade dependencies (`uv sync --upgrade`) |
| `just clean` | Remove caches, venv, coverage artifacts |
| `just fresh` | Clean + install |

### Containers

| Command | Description |
|---------|-------------|
| `just docker-build` | Build container image |
| `just docker-run` | Run container with env-file |
| `just docker-logs` | Tail container logs |

## Development Workflow

1. **Implement feature** — Keep routers thin; business logic in `services/`
2. **Add/adjust models** — Define schemas in `app/models/`
3. **Write tests** — Unit tests for services/models; integration tests for API routes
4. **Run checks** — `just lint && just typing`
5. **Run targeted tests** — `just test tests/integration/routers/test_profile.py::TestCreateProfile`
6. **Run coverage** — `just cov` before PR
7. **Commit** — Use Conventional Commit style

## Middleware Stack

Middleware order (outermost to innermost):
1. **RequestContextLogMiddleware** — JSON logging with trace correlation
2. **SecurityHeadersMiddleware** — Adds security headers (HSTS, X-Frame-Options, etc.)
3. **BodySizeLimitMiddleware** — Rejects oversized requests with 413
4. **CORSMiddleware** — Handles preflight and CORS headers

### CORS

CORS is deny-by-default. Set `CORS_ORIGINS` to explicit origins for browser clients.

### Security Headers

Adds: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`. HSTS enabled when HTTPS and not in debug mode.

### Request Size Limits

`BodySizeLimitMiddleware` aborts with 413 if body exceeds `MAX_REQUEST_SIZE_BYTES`. Uses streaming check (pre-checks `Content-Length`, then counts chunks incrementally).

## Logging & Trace Correlation

JSON logs with keys: `severity`, `message`, `time`, `logger`, source location, optional `trace`/`spanId` from `X-Cloud-Trace-Context` header (Cloud Run/GCP).

```python
logger.info("profile created", extra={"user_id": uid, "profile_id": uid})
```

Audit events via `log_audit_event()`:
```python
from app.middleware import log_audit_event
log_audit_event("create", user_id, "profile", user_id, "success")
```

## Authentication Flow

1. Client obtains Firebase ID token (via Firebase Auth SDK)
2. Client sends header: `Authorization: Bearer <id_token>`
3. Server verifies token with revocation check via `verify_firebase_token`
4. Returns `FirebaseUser(uid, email, email_verified)`

**Failure cases:**
- Missing header → 403 (HTTPBearer security scheme)
- Invalid/expired/revoked token → 401 `{"detail": "Unauthorized"}`

## Domain Exceptions

Custom exceptions with HTTP semantics in `app/exceptions/`:

| Exception | Status | Use Case |
|-----------|--------|----------|
| `DomainError` | 500 | Base class |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Resource conflict |
| `ProfileNotFoundError` | 404 | Profile not found |
| `ProfileAlreadyExistsError` | 409 | Profile already exists |

Exception handlers in `app/core/handlers/` automatically convert domain exceptions to HTTP responses.

## Firestore Service

`ProfileService` uses async Firestore operations with `@firestore.async_transactional` for atomic operations. Firebase token verification runs in thread pool via `asyncio.to_thread()` to avoid blocking.

## Testing

| Category | Path | Focus |
|----------|------|-------|
| Unit | `tests/unit/**` | Models, config, services, middleware |
| Integration | `tests/integration/**` | API routes, request/response flows |
| E2E | `tests/e2e/**` | Real Firebase emulator tests |

**Commands:**
```bash
just test               # Unit + integration (CI-compatible)
just test-unit          # Unit tests only
just test-integration   # Integration tests only
just test-e2e           # E2E tests (requires: just emulators)
just test-all           # All tests including E2E
just cov                # Coverage report (html/json)
```

**Examples:**
```bash
just test-unit tests/unit/models/test_profile_model.py
just test-integration tests/integration/routers/test_profile.py::TestCreateProfile
```

**Notes:**
- Unit/integration tests mock Firebase/Firestore; no real network calls
- E2E tests require Firebase emulators: run `just emulators` first

## Error Responses

Standard error shape (`ErrorResponse`):
```json
{"detail": "<message>"}
```

Validation errors keep FastAPI's default list format (422 responses).

## Example Requests

**Create a profile:**
```bash
curl -X POST http://localhost:8080/profile/ \
  -H "Authorization: Bearer <firebase_id_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "firstname": "John",
    "lastname": "Doe",
    "email": "john@example.com",
    "phone_number": "+358401234567",
    "terms": true
  }'
```

**Get profile:**
```bash
curl http://localhost:8080/profile/ \
  -H "Authorization: Bearer <firebase_id_token>"
```

**Update profile (partial):**
```bash
curl -X PATCH http://localhost:8080/profile/ \
  -H "Authorization: Bearer <firebase_id_token>" \
  -H "Content-Type: application/json" \
  -d '{"firstname": "Jane", "marketing": true}'
```

**Delete profile:**
```bash
curl -X DELETE http://localhost:8080/profile/ \
  -H "Authorization: Bearer <firebase_id_token>"
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
just docker-build pyimg=python:3.14-slim-bookworm
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
  --base-image python:3.14-slim \
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

- Runtime: Python 3.14 (`"runtime": "python314"` in `firebase.json`).
- Region: `europe-west4` (set globally via `options.set_global_options`).
- Memory: 128 MB (`memory=options.MemoryOption.MB_128`).
- Scaling limits (env-configurable):
  - `MIN_INSTANCES` (default 0)
  - `MAX_INSTANCES` (default 2)
- Example function: `on_request_example` returns a simple "Hello world!" response.
- Dependencies managed via `functions/pyproject.toml` (uses uv by default on Python 3.14+; keep lean to reduce cold starts).

### Project Config (firebase.json excerpt)

```jsonc
{
  "functions": [
    {
      "source": "functions",
      "location": "europe-west4",
      "codebase": "default",
      "runtime": "python314"
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
cd functions
uv sync                                # Install dependencies
export FUNCTIONS_DISCOVERY_TIMEOUT=30  # Helps CLI module scan (avoid premature timeout)
firebase deploy --only functions
```

Common one-liner:
```bash
cd functions && uv sync && firebase deploy --only functions
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

**CI Workflow** (`.github/workflows/ci.yml`):
1. Checkout + Python 3.14 setup
2. Install dependencies (`just install`)
3. Lint (`just lint`)
4. Type checking (`just typing`)
5. Coverage tests (`just cov` + htmlcov artifact upload)
6. Coverage comment on PRs

**Label Automation:**
- Auto-labeling: `.github/workflows/labeler.yml`
- Manual backfill: `.github/workflows/labeler-manual.yml`

## Development Conventions

- **Routers thin** — Put business logic in `services/`
- **Async endpoints** — Use `async def` for I/O-bound operations
- **Type hints everywhere** — Ruff `ANN` rules enforce annotations
- **Import grouping** — stdlib / third-party / local with blank lines
- **Config access** — Use `get_settings()`, never read env directly
- **No secrets in logs** — Redact sensitive fields
- **Isolated tests** — Mock external services, no network calls
- **Dependency injection** — Use typed aliases from [app/dependencies.py](app/dependencies.py) (`CurrentUser`, `ProfileServiceDep`)

## Gotchas & Tips

| Area | Issue | Solution |
|------|-------|----------|
| CORS | Empty `CORS_ORIGINS` denies all | Set explicit origins for browser clients |
| Body size | Hard 413 at limit | Communicate limit to clients uploading large payloads |
| Firebase Auth | Blocking SDK call | Token verification runs via `asyncio.to_thread()` |
| Firestore | Async client required | Use `get_async_firestore_client()` for async ops |
| Pydantic v2 | API changes from v1 | Use `model_dump()` not `.dict()`, `model_validate()` not `.parse_obj()` |
| Trailing slashes | FastAPI redirects without | Always use paths with trailing slash (e.g., `/profile/`) |

## For AI Assistants

**Adding an endpoint:**
1. Define request/response models in `app/models/` (use `Field(examples=[...])` for all fields)
2. Add domain exceptions in `app/exceptions/` if needed
3. Implement service logic in `app/services/`
4. Create router in `app/routers/` using `APIRouter` with tags and `operation_id`
5. Register router in [app/main.py](app/main.py)
6. Add unit tests for service, integration tests for route

**Adding configuration:**
1. Add field in `Settings` class ([app/core/config.py](app/core/config.py))
2. Access via `get_settings()` in application code
3. Update this README if user-facing

**Adding domain exceptions:**
1. Create exception class in `app/exceptions/` inheriting from `DomainError`/`NotFoundError`/`ConflictError`
2. Set `status_code` and `detail` class attributes
3. Export from [app/exceptions/__init__.py](app/exceptions/__init__.py)
4. Exception handlers auto-convert to HTTP responses

**Key patterns:**
- Use `CurrentUser` and `ProfileServiceDep` type aliases for dependency injection
- Profile router uses `PATCH` for partial updates (not `PUT`)
- All routes have `operation_id` for stable SDK generation (pattern: `<resource>_<action>`)
- Response models use `ProfileResponse` wrapper with `success`, `message`, `profile` fields

## License

MIT License — see [LICENSE](LICENSE).
