# FastAPI Playground

A FastAPI application demonstrating Firebase Authentication, Firestore CRUD operations, and modern Python development workflow using `uv` (dependency & virtualenv manager) and `just` (task runner).

<img src="assets/python.svg" alt="Python logo" width="400">

<sub>Python logo from [python.org](https://www.python.org/community/logos/). Trademark of the Python Software Foundation.</sub>

## Features

- Layered middleware architecture with security headers, CORS, request IDs, and structured access logs
- Request-scoped logging with Google Cloud Trace correlation via [W3C Trace Context](https://www.w3.org/TR/trace-context/) `traceparent` header
- [RFC 9457 Problem Details](https://datatracker.ietf.org/doc/html/rfc9457) for all error responses with field-level validation errors
- Content negotiation supporting [JSON (RFC 8259)](https://datatracker.ietf.org/doc/html/rfc8259) and [CBOR (RFC 8949)](https://datatracker.ietf.org/doc/html/rfc8949) formats via `Accept` header
- Cursor-based pagination with [RFC 8288 Link](https://datatracker.ietf.org/doc/html/rfc8288) headers
- [OpenAPI 3.1](https://spec.openapis.org/oas/v3.1.0) documentation with Swagger UI and ReDoc
- Firebase Authentication with ID token verification and revocation checks
- Firestore persistence with async transactional operations
- Health check endpoint (`/health`) for liveness probes

## API Design Principles

### URI Design

- Use plural nouns for collections (`/items/`, not `/item/`)
- Avoid verbs in URIs; let HTTP methods convey the action
- Return resources directly without wrapper envelopes

### HTTP Methods & Status Codes

| Method | Purpose | Success Status |
|--------|---------|----------------|
| GET | Retrieve resource(s) | 200 OK |
| POST | Create a resource | 201 Created + Location header |
| PATCH | Partial update | 200 OK |
| DELETE | Remove a resource | 204 No Content |

### Error Responses

Errors follow [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html) and honor content negotiation:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Profile not found"
}
```

Validation errors (422) include detailed field locations:

```json
{
  "type": "about:blank",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed",
  "errors": [
    {"location": "body.email", "message": "value is not a valid email address", "value": "invalid"}
  ]
}
```

### Content Negotiation

- Default: `application/json`
- Alternate: `application/cbor`
- Format selected via `Accept` header

### Pagination

- Cursor-based tokens for stability
- Links provided via HTTP `Link` header per [RFC 8288](https://www.rfc-editor.org/rfc/rfc8288.html)

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- [just](https://github.com/casey/just) command runner
- Firebase project with Authentication and Firestore enabled

## Quick Start

```bash
git clone <repository-url>
cd fastapi-playground
just install        # Install dependencies via uv
just serve          # Start dev server at http://127.0.0.1:8080
```

Then visit:
- `http://localhost:8080/health` - service health probe
- `http://localhost:8080/api-docs` - interactive API explorer (Swagger UI)
- `http://localhost:8080/api-redoc` - API documentation (ReDoc)

Sample request:
```bash
curl -s localhost:8080/health | jq
```

## Environment Variables

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Server listen port | `8080` |
| `HOST` | Host address to bind to | `0.0.0.0` |
| `ENVIRONMENT` | Environment label | `production` |
| `DEBUG` | Enable debug mode | `false` |
| `FIREBASE_PROJECT_ID` | Firebase/GCP project ID | - |
| `FIREBASE_PROJECT_NUMBER` | Numeric project number (optional) | - |
| `FIRESTORE_DATABASE` | Firestore database ID | `(default)` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service account JSON path (local dev) | - |
| `CORS_ORIGINS` | Comma-separated allowed origins | - |
| `MAX_REQUEST_SIZE_BYTES` | Request body size limit | `1000000` |

## Project Layout

```
app/
  main.py              # FastAPI app factory and lifespan manager
  dependencies.py      # Dependency injection (CurrentUser, ProfileServiceDep)
  api/                 # API route handlers
    health.py          # Health check endpoint
    hello.py           # Hello greeting endpoints
    items.py           # Items with pagination
    profile.py         # Profile CRUD (Firebase Auth protected)
  auth/                # Firebase authentication
    firebase.py        # Token verification, FirebaseUser
  core/                # Configuration and infrastructure
    config.py          # Settings class (pydantic-settings)
    firebase.py        # Firebase Admin SDK and async Firestore client
    exception_handler.py  # RFC 9457 Problem Details
    cbor.py            # CBOR content negotiation
  exceptions/          # Domain exceptions using fastapi-problem
    base.py            # Base exception classes
    profile.py         # ProfileNotFoundError, ProfileAlreadyExistsError
  middleware/          # ASGI middleware stack
    body_limit.py      # Request size guard (413 on oversized)
    logging.py         # JSON logging with trace correlation
    security.py        # Security headers (HSTS, X-Frame-Options)
  models/              # Pydantic schemas
    error.py           # ProblemResponse schema
    types.py           # Shared types (NormalizedEmail, Phone, UtcDatetime)
    health/            # Health response models
    hello/             # Hello response models
    items/             # Items response models
    profile/           # Profile domain models
  pagination/          # Cursor-based pagination
    cursor.py          # Cursor encoding/decoding
    link.py            # RFC 8288 Link header builder
    paginator.py       # Pagination helper
  services/            # Business logic layer
    profile/           # ProfileService with Firestore operations
tests/
  unit/                # Unit tests (mocked dependencies)
  integration/         # API route tests (TestClient)
  e2e/                 # Firebase emulator tests (local only)
  helpers/             # Shared test utilities
functions/             # Firebase Cloud Functions (Python 3.14)
  main.py              # HTTPS callable example
  pyproject.toml       # Functions-specific dependencies
```

## Routes

All routes use paths without trailing slashes (`redirect_slashes=False`).

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check probe |
| GET | `/v1/hello` | No | Default greeting |
| POST | `/v1/hello` | No | Personalized greeting |
| GET | `/v1/items` | No | List items with pagination |
| POST | `/v1/profile` | Yes | Create user profile |
| GET | `/v1/profile` | Yes | Get user profile |
| PATCH | `/v1/profile` | Yes | Update user profile |
| DELETE | `/v1/profile` | Yes | Delete user profile |

Protected routes require `Authorization: Bearer <Firebase ID token>` header.

## Development

### Build and Test

```bash
just lint            # Run Ruff check + format
just typing          # Run ty type checker
just test            # Run unit + integration tests
just test-unit       # Unit tests only
just test-integration  # Integration tests only
just cov             # Run tests with coverage report
```

### Justfile Commands

| Command | Description |
|---------|-------------|
| `just serve` | Start dev server with hot reload |
| `just browser` | Open dev server in browser |
| `just lint` | Run Ruff check + format |
| `just typing` | Type checking via ty |
| `just test` | Unit + integration tests |
| `just cov` | Coverage report (html/json) |
| `just check` | lint + typing + test |
| `just emulators` | Start Firebase emulators for E2E |

Run `just` to see all available commands.

### Dependencies

```bash
just install         # Install/sync dependencies
just update          # Upgrade dependencies
just fresh           # Clean + reinstall
```

## Adding Routes

1. Create models in `app/models/<resource>/` with request/response schemas
2. Add domain exceptions in `app/exceptions/` if needed
3. Implement service logic in `app/services/<resource>/`
4. Create handler in `app/api/<resource>.py` using `APIRouter`
5. Register router in `app/main.py`
6. Add unit tests for service, integration tests for routes

## Container

```bash
just container-build    # Build image
just container-up       # Run container
just container-logs     # View container logs
just container-down     # Stop container
```

Or with Docker/Podman CLI:
```bash
docker build -t fastapi-playground:latest .
docker run --rm -p 8080:8080 --env-file .env fastapi-playground:latest
```

## Deployment

### Google Cloud Run

```bash
# Build and push to Artifact Registry
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/REPO/fastapi-playground:latest

# Deploy with automatic base image updates
gcloud run deploy fastapi-playground \
  --image REGION-docker.pkg.dev/PROJECT_ID/REPO/fastapi-playground:latest \
  --platform managed \
  --region REGION \
  --base-image python314 \
  --automatic-updates

# Deploy from source with automatic base image updates
gcloud run deploy fastapi-playground \
  --source . \
  --platform managed \
  --region REGION \
  --base-image python314 \
  --automatic-updates
```

The `--base-image` and `--automatic-updates` flags enable [automatic base image updates](https://cloud.google.com/run/docs/configuring/services/automatic-base-image-updates), allowing Google to apply security patches to the OS and runtime without rebuilding or redeploying.

Set `FIREBASE_PROJECT_ID` environment variable to enable trace correlation in Cloud Logging.

For detailed infrastructure setup, see [GCP.md](GCP.md).

### Firebase Cloud Functions

```bash
cd functions
uv sync
firebase deploy --only functions
```

See [functions/README.md](functions/README.md) for Cloud Functions documentation.

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Description |
|----------|-------------|
| `app-ci.yml` | Build, tests, and coverage report |
| `app-lint.yml` | Code quality (Ruff linting and formatting) |
| `labeler.yml` | Automatic PR labeling |
| `labeler-manual.yml` | Manual labeling for historical PRs |
| `dependabot-auto-merge.yml` | Auto-merge Dependabot minor/patch updates |

Dependabot is configured in `.github/dependabot.yml` for automated dependency updates.

## Contributing

See [AGENTS.md](AGENTS.md) for coding guidelines and conventions.

## License

MIT - see [LICENSE](LICENSE).
