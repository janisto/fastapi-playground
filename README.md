# FastAPI Playground

A FastAPI application demonstrating Firebase Authentication, Firestore CRUD operations, and modern Python development workflow using `uv` (dependency & virtualenv manager) and `just` (task runner).

<img src="assets/python.svg" alt="Python logo" width="400">

<sub>Python logo from [python.org](https://www.python.org/community/logos/). Trademark of the Python Software Foundation.</sub>

## Features

- Layered middleware architecture with security headers, CORS, request IDs, and structured access logs via [`fastapi-request-observability`](https://pypi.org/project/fastapi-request-observability/)
- Request-scoped logging with Google Cloud Trace correlation via [W3C Trace Context](https://www.w3.org/TR/trace-context/) `traceparent` header
- [RFC 9457 Problem Details](https://datatracker.ietf.org/doc/html/rfc9457) for all error responses with field-level validation errors
- JSON and CBOR request/response content negotiation using `Content-Type` and `Accept`
- Cursor-based pagination with [RFC 8288 Link](https://datatracker.ietf.org/doc/html/rfc8288) headers
- [OpenAPI 3.1](https://spec.openapis.org/oas/v3.1.0) documentation with Swagger UI and ReDoc
- Firebase Authentication with ID token verification and revocation checks
- Firestore persistence with async transactional operations
- Health check endpoint (`/health`) for liveness probes

## API Design Principles

### URI Design

- Use plural nouns for collections (`/items`, not `/item`)
- Avoid verbs in URIs; let HTTP methods convey the action
- Return resources directly without wrapper envelopes

### HTTP Methods & Status Codes

| Method | Purpose | Success Status |
|--------|---------|----------------|
| GET | Retrieve resource(s) | 200 OK |
| POST | Create a resource | 201 Created; persistent resources include a Location header |
| PATCH | Partial update | 200 OK |
| DELETE | Remove a resource | 204 No Content |

### Error Responses

Errors follow [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html) and honor content negotiation:

```json
{
  "$schema": "https://api.example.com/schemas/ProblemResponse.json",
  "title": "Not Found",
  "status": 404,
  "detail": "Profile not found"
}
```

Validation errors (422) include detailed field locations:

```json
{
  "$schema": "https://api.example.com/schemas/ValidationProblemResponse.json",
  "title": "Unprocessable Entity",
  "status": 422,
  "detail": "validation failed",
  "errors": [
    {"location": "body.email", "message": "value is not a valid email address", "value": "invalid"}
  ]
}
```

### Content Negotiation

- Responses default to `application/json`; request `application/cbor` explicitly with `Accept`.
- JSON and CBOR request bodies are selected with `Content-Type`.
- Explicit exclusions such as `application/cbor;q=0` are honored.

### Pagination

- Cursor-based tokens for stability
- Links provided via HTTP `Link` header per [RFC 8288](https://www.rfc-editor.org/rfc/rfc8288.html)

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- [just](https://github.com/casey/just) command runner
- Firebase project with Authentication and Firestore enabled
- [Firebase CLI](https://firebase.google.com/docs/cli) for emulators and Functions deployment

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
| `ENVIRONMENT` | Environment label | `production` |
| `DEBUG` | Enable debug mode | `false` |
| `FIREBASE_PROJECT_ID` | Firebase/GCP project ID | - |
| `FIRESTORE_DATABASE` | Firestore database ID | `(default)` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service account JSON path (local dev) | - |
| `CORS_ORIGINS` | JSON array or comma-separated allowed origins | - |
| `MAX_REQUEST_SIZE_BYTES` | Request body size limit | `1000000` |

### Firebase and Cloud Logging MCP clients

The workspace MCP configurations in `.vscode/mcp.json` and `.codex/config.toml` use the Firebase CLI server and the
managed Cloud Logging server. Firebase uses the credentials available to the Firebase CLI. Cloud Logging reads the
quota project and a short-lived Application Default Credentials access token from the shell environment.

First align the gcloud default project and the Application Default Credentials quota project:

```bash
gcloud config set project PROJECT_ID
gcloud auth application-default login
gcloud auth application-default set-quota-project PROJECT_ID
```

For zsh, add these public, secret-free definitions to `~/.zshrc`:

```bash
export GOOGLE_CLOUD_PROJECT="PROJECT_ID"
export GOOGLE_CLOUD_ACCESS_TOKEN="$(gcloud auth application-default print-access-token)"
```

Run `source ~/.zshrc`, then restart VS Code or Codex so the client inherits the variables. The access token is
short-lived; opening a new shell regenerates it, while a long-running client must be restarted after a refresh. Never
commit the expanded token. Keep this convenience setup to a trusted workstation because child processes inherit the
token. See [GCP.md](GCP.md) for IAM and troubleshooting details.

## Project Layout

```
.agents/skills/        Five portable project workflows with Codex UI metadata
.github/agents/       Evidence-based security review profile for GitHub Copilot
app/
  main.py              # FastAPI composition, lifespan, and outer ASGI middleware
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
    logging.py         # Structured JSON logging configuration
    firebase.py        # Firebase Admin SDK and async Firestore client
    exception_handler.py  # RFC 9457 Problem Details
    cbor.py            # CBOR content negotiation
  exceptions/          # Domain exceptions using fastapi-problem
    profile.py         # ProfileNotFoundError, ProfileAlreadyExistsError
  middleware/          # ASGI middleware stack
    body_limit.py      # Request size guard (413 on oversized)
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
  main.py              # HTTP dad-joke function
  pyproject.toml       # Functions-specific dependencies
```

Repository guidance follows the canonical [AGENTS.md format](https://github.com/agentsmd/agents.md). Portable skills
use the canonical [Agent Skills specification and documentation](https://github.com/agentskills/agentskills), with the
detailed [format specification](https://agentskills.io/specification), under `.agents/skills/`. See
[AGENTS.md](AGENTS.md) for the working rules and current skill catalog.

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
| GET | `/schemas/{schema_name}` | No | Retrieve a generated JSON Schema |

Protected routes require `Authorization: Bearer <Firebase ID token>` header.

## Development

### Build and Test

```bash
just lint               # Check Ruff linting and formatting
just typing             # Type-check the FastAPI app
just typing-functions   # Type-check the separate Functions project
just test               # Run unit + integration tests
just test-unit          # Run unit tests only
just test-integration   # Run integration tests only
just test-e2e           # Run emulator E2E tests, or skip when emulators are absent
just test-all           # Run every test tier
just cov                # Generate HTML and JSON coverage reports
```

### Justfile Commands

| Command | Description |
|---------|-------------|
| `just serve` | Start dev server with hot reload |
| `just browser` | Open dev server in browser |
| `just lint` | Check Ruff linting and formatting |
| `just typing` | Type checking via ty |
| `just typing-functions` | Type-check the separate Functions project |
| `just test` | Unit + integration tests |
| `just test-e2e` | Firebase emulator E2E tests |
| `just test-all` | All test tiers |
| `just cov` | Coverage report (html/json) |
| `just check` | lint + typing + test |
| `just emulators` | Start Firebase emulators for E2E |

Run `just` to see all available commands.

### Dependencies

```bash
just install         # Install/sync dependencies
just install-functions  # Install/sync Functions dependencies
just update          # Upgrade root and Functions dependencies
just fresh           # Clean + reinstall
```

## Adding Routes

1. Create models in `app/models/<resource>/` with request/response schemas
2. Add domain exceptions in `app/exceptions/` if needed
3. Implement service logic in `app/services/<resource>/`
4. Create handler in `app/api/<resource>.py` using `APIRouter`
5. Register business routers in `app/api/__init__.py`; keep health and schema discovery unversioned in `app/main.py`
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

Profile requests also require Application Default Credentials or a service-account credential mounted into the
container. The `just container-up` recipe mounts `service_account.json` by default; override its `creds` argument when
using another local path.

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
uv venv --python 3.14 venv
uv pip install --python venv/bin/python -r requirements.txt
firebase deploy --only functions
```

See [functions/README.md](functions/README.md) for Cloud Functions documentation.

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Description |
|----------|-------------|
| `app-ci.yml` | App and Functions quality checks plus app test coverage |
| `app-lint.yml` | Code quality (Ruff linting and formatting) |
| `labeler.yml` | Automatic PR labeling |
| `labeler-manual.yml` | Manual labeling for historical PRs |
| `dependabot-auto-merge.yml` | Auto-merge Dependabot minor/patch updates |

Dependabot is configured in `.github/dependabot.yml` for automated dependency updates.

## Contributing

See [AGENTS.md](AGENTS.md) for coding guidelines and conventions.

## License

MIT - see [LICENSE](LICENSE).
