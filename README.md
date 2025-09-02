# FastAPI Playground

A small FastAPI app showcasing Firebase Authentication, Firestore CRUD, typed models, and a tidy dev workflow with uv and just.

## Features

- FastAPI (Python 3.13+) with async endpoints and automatic OpenAPI docs
- Firebase Authentication (verify ID tokens via Admin SDK)
- Firestore for storing user profile data
- Structured JSON logging to stdout (Cloud Run friendly)
- Pydantic v2 models and pydantic-settings for configuration
- Tests with pytest + pytest-asyncio; coverage reporting
- Linting/formatting with Ruff and type checking with ty
- Strict security headers middleware and configurable CORS allowlist (deny-by-default)
- Request body size limit middleware (413 on exceeding MAX_REQUEST_SIZE_BYTES)

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── dependencies.py         # Application dependencies
│   ├── auth/
│   │   ├── __init__.py
│   │   └── firebase.py         # Firebase authentication
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Application configuration
│   │   ├── firebase.py         # Firebase initialization
│   │   ├── logging.py          # Logging configuration
│   │   ├── security.py         # Security headers middleware
│   │   └── body_limit.py       # Request size limit middleware
│   ├── models/
│   │   ├── __init__.py
│   │   └── profile.py          # Profile data models
│   ├── routers/
│   │   └── profile.py          # Profile API endpoints
│   └── services/
│       ├── __init__.py
│       └── profile.py          # Profile business logic
├── tests/
│   ├── test_e2e.py            # End-to-end tests
│   ├── test_models.py         # Model validation tests
│   └── test_auth.py           # Authentication tests
├── .github/
│   └── workflows/
│       └── check-all.yml      # CI: lint, typing, tests, coverage artifact
├── pyproject.toml             # Project configuration
├── Justfile                   # Task runner commands
├── Dockerfile                 # Container build for deployment
└── README.md
```

## API Endpoints

### Root Endpoints
- `GET /` - Hello World message with API docs link
- `GET /health` - Health check endpoint
- `GET /api-docs` - Interactive API documentation (Swagger UI)
- `GET /api-redoc` - Alternative API documentation (ReDoc)

### Profile Endpoints (Protected)
All profile endpoints require Firebase JWT via `Authorization: Bearer <token>`.

- `POST /profile/` - Create user profile
- `GET /profile/` - Get user profile
- `PUT /profile/` - Update user profile
- `DELETE /profile/` - Delete user profile

## Profile Model

```python
{
  "firstname": str,          # First name (required)
  "lastname": str,           # Last name (required)
  "email": EmailStr,         # Email address (required, validated)
  "phone_number": str,       # Phone number (required)
  "marketing": bool,         # Marketing opt-in (default: false)
  "terms": bool,             # Terms acceptance (required)
  "id": str,                 # User ID (auto-generated)
  "created_at": datetime,    # Creation timestamp (auto-generated)
  "updated_at": datetime     # Update timestamp (auto-generated)
}
```

## Prerequisites

- Python 3.13+
- uv (package manager)
- just (command runner)
- Firebase project (Authentication + Firestore)
- Google Cloud project (optional for Cloud Logging in production)

## Tech stack and pinned versions

Core dependencies (from uv.lock):
- FastAPI 0.116.1 (Starlette 0.47.3)
- Pydantic 2.11.7 and pydantic-settings
- Uvicorn 0.35.0
- Firebase Admin SDK 7.1.0 (Firestore client)
- httpx (used by tools/tests)

## Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd fastapi-playground
   ```

2. **Install dependencies**
   ```bash
   just install
   ```

3. **Create a .env file** (loaded automatically by pydantic-settings)
   Required/optional keys:
   - ENVIRONMENT=development|production
   - DEBUG=true|false
   - HOST=0.0.0.0
   - PORT=8080
   - FIREBASE_PROJECT_ID=your-firebase-project-id
   - GCP_PROJECT_ID=your-gcp-project-id
   - GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json (optional; uses ADC if unset)
   - SECRET_MANAGER_ENABLED=true|false (optional)
   - FIRESTORE_COLLECTION_PROFILES=profiles (optional)
   - MAX_REQUEST_SIZE_BYTES=1000000 (optional; default 1,000,000 bytes)
   - CORS_ORIGINS=https://example.com,https://app.example.com (optional; empty by default denies all origins)

4. **Configure Firebase**
   - Create a Firebase project at https://console.firebase.google.com/
   - Enable Authentication and Firestore Database
   - Download service account key JSON file
   - Either set `GOOGLE_APPLICATION_CREDENTIALS` or ensure Application Default Credentials are configured

5. **Set up Google Cloud** (optional but recommended for prod)
   - Enable required APIs: Firestore, Cloud Logging, Secret Manager
   - Ensure your service account has necessary permissions

## Available Commands (via just)

```bash
# Discover all tasks
just

# Development
just serve                    # Run dev server at http://127.0.0.1:${PORT:-8080}
just browser                  # Open dev server in browser
just req <path> [args...]     # Send HTTP request via httpie (e.g. `just req health`)

# Quality
just test [pytest-args...]    # Run tests
just cov                      # Tests with coverage (HTML -> htmlcov/)
just lint                     # Ruff check + format
just modernize                # Apply safe modernization via Ruff's pyupgrade rules
just typing                   # Type checking via ty
just check-all                # Lint + typing + test

# Lifecycle
just install                  # Install deps (uv sync)
just update                   # Upgrade deps
just clean                    # Remove caches/venv/coverage artifacts
just fresh                    # Clean and reinstall

# Container
just docker-build [image=fastapi-playground:local] [pyimg=python:3.13-slim]
just docker-run [image=fastapi-playground:local] [env_file=.env] [name=fastapi-playground]
just docker-logs [name=fastapi-playground]
```

## Useful CLI Commands

| Command                                                      | Purpose                                                                 |
| ------------------------------------------------------------ | ----------------------------------------------------------------------- |
| `uv sync`                                                    | Install project dependencies without just.                              |
| `uv run -m pytest`                                           | Run tests without just.                                                 |
| `uvx ruff check`                                             | Run Ruff linter directly.                                               |
| `uvx ruff format`                                            | Apply Ruff formatter.                                                   |
| `docker build -t fastapi-playground:local .`                 | Build local Docker image.                                               |
| `docker run --rm -p 8080:8080 --env-file .env IMAGE`         | Run container locally with env file and port mapping.                   |
| `gcloud run deploy ... --automatic-updates --base-image ...` | Deploy to Cloud Run with automatic base image updates (see Deployment). |

## Development

### Running the Application

```bash
# Start development server
just serve
```

The application will be available at:
- API: http://localhost:8080
- Documentation: http://localhost:8080/api-docs
- Health Check: http://localhost:8080/health

### CORS and security headers

- CORS is deny-by-default. To allow specific origins, set `CORS_ORIGINS` to a comma-separated list (no spaces required; spaces are trimmed).
- Common security headers are added for every response (X-Content-Type-Options, X-Frame-Options, Referrer-Policy). HSTS is added automatically on HTTPS when `DEBUG=false`.

### Request size limits

- Requests exceeding `MAX_REQUEST_SIZE_BYTES` are rejected early with HTTP 413 without buffering the full body.
- Adjust the limit via the env var if you accept large JSON uploads.

### Running Tests

```bash
# Run all tests
just test

# Run with coverage
just cov

# Run specific test file
just test tests/test_models.py
```

### Code Quality

```bash
# Lint and format code
just lint

# Type checking
just typing

# Run all quality checks
just check-all
```

## Authentication

The API uses Firebase Authentication with JWT ID tokens. To access protected endpoints:

1. Authenticate users through Firebase Auth (frontend/mobile app)
2. Obtain ID token from Firebase
3. Include token in requests: `Authorization: Bearer <id_token>`

Example using curl:
```bash
# Get profile (replace <token> with actual Firebase ID token)
curl -H "Authorization: Bearer <token>" http://localhost:8080/profile/

# Create profile
curl -X POST \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"firstname":"John","lastname":"Doe","email":"john@example.com","phone_number":"+1234567890","terms":true}' \
  http://localhost:8080/profile/
```

## Deployment

### Google Cloud Run

1. **Build container**
   ```bash
   # default base (Dockerfile ARG): python:3.13-alpine
    docker build -t gcr.io/PROJECT_ID/fastapi-playground .

   # optionally override the base used at build time (recommended: slim variants)
    docker build \
      --build-arg PYTHON_IMAGE=python:3.13-slim-bookworm \
       -t gcr.io/PROJECT_ID/fastapi-playground .
   ```

2. **Push to Container Registry**
   ```bash
   docker push gcr.io/PROJECT_ID/fastapi-playground
   ```

3. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy fastapi-playground \
     --image gcr.io/PROJECT_ID/fastapi-playground \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

#### Enable automatic base image updates

Link your service to a managed base and let Cloud Run apply security patches automatically without creating new revisions:

```bash
gcloud run deploy fastapi-playground \
   --image gcr.io/PROJECT_ID/fastapi-playground:TAG \
   --base-image python:3.13-slim \
   --automatic-updates
```

Notes
- Keep `PYTHON_IMAGE` used at build time aligned with `--base-image` to avoid surprises.
- For source-based deploys, you can also do: `gcloud run deploy --source . --base-image python:3.13-slim --automatic-updates`.

### Environment Variables for Production

Set these environment variables in your deployment:
- `ENVIRONMENT=production`
- `DEBUG=false`
- `FIREBASE_PROJECT_ID=your-project-id`
- `GCP_PROJECT_ID=your-project-id`
 - `GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json` (or use ADC)

## Logging on Cloud Run

This app emits one-line JSON logs to stdout using a lightweight formatter (`app/core/logging.py`). Cloud Run automatically forwards stdout/stderr to Cloud Logging, avoiding the overhead of using Cloud Logging API handlers inside your app process.

What’s in each log line:
- severity: Cloud Logging severity derived from Python level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- message: the log message
- time / timestamp: RFC3339 with microseconds (UTC)
- logger: logger name
- logging.googleapis.com/sourceLocation: file, line, function (helps in debugging)
- Optional: trace and spanId (when available)

Trace correlation (X-Cloud-Trace-Context):
- When a request includes `X-Cloud-Trace-Context: TRACE_ID/SPAN_ID;o=1`, middleware adds:
   - `trace = projects/<GCP_PROJECT_ID>/traces/<TRACE_ID>`
   - `spanId = <SPAN_ID>`
- This lets you filter logs by request and view them alongside Cloud Trace.

Structured extras:
- You can attach fields via `extra={...}`: `logger.info("created", extra={"user_id": "123"})`.
- `None` values are coerced to the string "null" to prevent Cloud Logging from nesting labels under `jsonPayload`.

Notes:
- Uvicorn logs are routed through the same JSON formatter for consistency.
- No dependency on the Cloud Logging client; safer memory profile under load.

### Example structured log

Emit a log with extra fields:

```python
import logging

logger = logging.getLogger(__name__)
logger.info(
      "created order",
      extra={
            "user_id": "u_123",
            "order_id": "ord_456",
            "labels": "checkout",
      },
)
```

Cloud Logging ingests the same line from stdout. It will look like this in the Logs Explorer (jsonPayload view simplified):

```json
{
   "severity": "INFO",
   "message": "created order",
   "time": "2025-01-01T12:00:00.123456+00:00",
   "timestamp": "2025-01-01T12:00:00.123456+00:00",
   "logger": "app.routers.example",
   "logging.googleapis.com/sourceLocation": {
      "file": "/workspace/app/routers/example.py",
      "line": 42,
      "function": "create_order"
   },
   "trace": "projects/your-gcp-project-id/traces/0123456789abcdef0123456789abcdef",
   "spanId": "123456",
   "user_id": "u_123",
   "order_id": "ord_456",
   "labels": "checkout"
}
```

## Testing

The project includes comprehensive testing:

- **Unit Tests**: Model validation, authentication logic
- **Integration Tests**: API endpoint testing with mocked dependencies
- **End-to-End Tests**: Full API workflow testing

Run specific test categories:
```bash
# Model tests
just test tests/test_models.py

# Authentication tests
just test tests/test_auth.py

# End-to-end tests
just test tests/test_e2e.py
```

Notes:
- Tests and E2E flows mock Firebase Admin and Firestore; no real network calls are made during `pytest`.
- Use `just cov` to generate an HTML report in `htmlcov/`.

## Container usage (local)

```bash
# Build (Docker must be running)
docker build -t fastapi-playground:local .

# Run on localhost:8080 (loads .env if needed via --env-file)
docker run --rm -p 8080:8080 --env-file .env fastapi-playground:local
```

Using just

```bash
# Build with default base and tag
just docker-build

# Build with a specific Python base
just docker-build pyimg=python:3.13-slim-bookworm

# Run on http://127.0.0.1:${PORT:-8080} with .env
just docker-run

# Use a custom image tag and env file
just docker-run image=gcr.io/PROJECT/fastapi-playground:local env_file=.env
```

## CI / Automation

- GitHub Actions workflow `.github/workflows/check-all.yml` runs on pull requests to `main`:
   - Installs dependencies with uv
   - Runs `just check-all` (lint, typing, tests with coverage)
   - Uploads HTML coverage as an artifact
   - On pull requests, posts a coverage comment and enforces thresholds (single-file ≥85%, total ≥90%).

## Conventions for contributors

- Use FastAPI style: async endpoints, thin routers, business logic in `services/`, shared utilities in `core/`.
- Type hints everywhere; avoid `Any`. Keep lines ≤120 chars (Ruff). Prefer explicit imports grouped stdlib / third-party / local.
- Config via `pydantic-settings` only; never read env directly in business logic. Don’t log secrets/PII.
- Prefer `uv` and `just` for all local tasks. Avoid mixing `pip/poetry` in this repo.

## External integrations

- Firebase Admin SDK for token verification and Firestore client.
- Google Cloud (optional) for Cloud Run and Cloud Logging ingestion via stdout.

## Development Guidelines

- Follow FastAPI style: async endpoints, thin routers; business logic in `services/`; shared config/logging in `core/`.
- Pydantic v2 models with explicit types; avoid `Any`.
- Never hardcode secrets. Load via env or Secret Manager. The app auto-loads `.env`.
- Logging configured via `app/core/logging.py`; Cloud Logging is enabled when `ENVIRONMENT=production`.
- For tests, external Firebase/Firestore calls are mocked; do not rely on real network during unit tests.

## Integration Notes & Gotchas

- Firebase Admin initialization happens in app lifespan (`app/main.py`). For local dev, set `GOOGLE_APPLICATION_CREDENTIALS` or use gcloud ADC.
- Missing `Authorization` header yields 403 (HTTPBearer); invalid/expired/revoked tokens return 401.
- Firestore access in `services/profile.py` is synchronous via the Google client; ensure credentials/project are set when running against real GCP.
- Default collection name is `profiles` (override with `FIRESTORE_COLLECTION_PROFILES`).
- Docker base image default is Alpine. Some uvicorn[standard] extras (uvloop, httptools) may compile on Alpine; if builds fail or are slow, pass `pyimg=python:3.13-slim*` to `just docker-build`.

## Error responses

Canonical error shape returned by the API follows `app/models/error.py`:

```json
{ "detail": "<message>" }
```

Examples: `{"detail":"Unauthorized"}`, `{"detail":"Profile not found"}`.

## Example Requests

```bash
# Using just + httpie helper to check health
just req health

# Using curl with auth token
curl -H "Authorization: Bearer <token>" http://localhost:8080/profile/

# Create profile
curl -X POST \
   -H "Authorization: Bearer <token>" \
   -H "Content-Type: application/json" \
   -d '{"firstname":"John","lastname":"Doe","email":"john@example.com","phone_number":"+1234567890","terms":true}' \
   http://localhost:8080/profile/
```

## GitHub Actions: Manually label PRs

This repository includes a manual workflow to apply labels to existing pull requests using `.github/labeler.yml` rules.

- Workflow name: "Manually Label PRs"
- File: `.github/workflows/labeler-manual.yml`

How to run
1. Go to GitHub → Actions tab.
2. Select "Manually Label PRs".
3. Click "Run workflow" and set inputs:
    - maxCount: Max number of PRs to process (default 200). Set 0 to process all found.
    - scope: Which PRs to consider: `closed` (default) or `all` (includes open and closed).
4. Start the run.

What it does
- Collects PR numbers based on the selected scope and caps to `maxCount`.
- Runs `actions/labeler@v5` for each PR with `sync-labels: true`.
   - Note: `sync-labels: true` will remove labels that no longer match the rules.

Requirements
- Ensure `.github/labeler.yml` contains your label rules (v5 format with `any`/`all` match blocks).

Troubleshooting
- If nothing matches, the matrix step is skipped (workflow succeeds with no changes).
- Large repos: consider a smaller `maxCount` and rerun if needed.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
