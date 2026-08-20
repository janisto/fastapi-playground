# FastAPI Playground

[![CI](https://img.shields.io/github/actions/workflow/status/janisto/fastapi-playground/app-ci.yml?branch=main&label=CI)](https://github.com/janisto/fastapi-playground/actions/workflows/app-ci.yml)
[![Lint](https://img.shields.io/github/actions/workflow/status/janisto/fastapi-playground/app-lint.yml?branch=main&label=lint)](https://github.com/janisto/fastapi-playground/actions/workflows/app-lint.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/github/license/janisto/fastapi-playground)](LICENSE)

A FastAPI reference application for the accepted portable playground API. It demonstrates strict JSON and CBOR
contracts, Firebase-authenticated Firestore profile lifecycle operations, a credential-free GitHub REST projection,
and a modern Python workflow using `uv` and `just`.

<img src="assets/python.svg" alt="Python logo" width="400">

<sub>Python logo from [python.org](https://www.python.org/community/logos/). Trademark of the Python Software Foundation.</sub>

## Features

- Layered middleware architecture with security headers, CORS, request IDs, and structured access logs via [`fastapi-request-observability`](https://pypi.org/project/fastapi-request-observability/)
- Request-scoped logging with incoming [W3C Trace Context](https://www.w3.org/TR/trace-context/) correlation metadata
- [RFC 9457 Problem Details](https://datatracker.ietf.org/doc/html/rfc9457) with stable error codes and value-free validation issues
- Strict JSON and CBOR parsing and RFC 9110 content negotiation using `Content-Type`, `Content-Encoding`, and `Accept`
- Cursor-based pagination with [RFC 8288 Link](https://datatracker.ietf.org/doc/html/rfc8288) headers
- Runtime [OpenAPI 3.1](https://spec.openapis.org/oas/v3.1.0) discovery at `/openapi.json`, with Swagger UI and ReDoc
- Firebase Authentication with ID token verification and revocation checks
- Atomic Firestore profile creation, patching, and deletion
- Six public GitHub operations through a fixed-origin, anonymous, bounded HTTP client
- Health check endpoint (`/health`) for liveness probes

## API Design Principles

### URI Design

- Use plural nouns for collections (`/items`, not `/item`)
- Avoid verbs in URIs; let HTTP methods convey the action
- Return resources directly without wrapper envelopes
- Use the exact lower camel case contract for public JSON and CBOR domain properties
- Keep implementation identifiers and persisted Firestore fields idiomatic `snake_case`; persistence names are not wire aliases

### HTTP Methods & Status Codes

| Method | Purpose | Success Status |
|--------|---------|----------------|
| GET | Retrieve resource(s) | 200 OK |
| POST | Process input and return a computed representation | 200 OK |
| POST | Create a resource | 201 Created; persistent resources include a Location header |
| PATCH | Partial update | 200 OK |
| DELETE | Remove a resource | 204 No Content |

### Error Responses

Errors follow [RFC 9457 Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html) and honor content negotiation:

```json
{
  "title": "Not Found",
  "status": 404,
  "detail": "Profile not found",
  "code": "profile_not_found"
}
```

Validation errors (422) include detailed field locations:

```json
{
  "title": "Unprocessable Content",
  "status": 422,
  "detail": "Request validation failed",
  "code": "validation_failed",
  "errors": [
    {"detail": "Request field is invalid", "source": {"pointer": "/contactEmail"}}
  ]
}
```

Validation documents identify only application-owned structure; they do not echo rejected values or unknown
attacker-controlled names. Standalone JSON Schema routes are a sibling extension. When a response advertises one, it
uses the registered lowercase relation, for example `Link: </schemas/Profile.json>; rel="describedby"`.

### Content Negotiation

- Portable API successes with a body default to `application/json`. CBOR is selected only when its effective quality
  is higher after RFC 9110 matching; wildcards and ties keep JSON.
- An explicit `Accept` value that excludes every supported success representation returns 406 before a
  representation-bearing endpoint executes. A 204 response has no representation, so `Accept` does not gate it.
- Schema discovery returns only `application/schema+json`. Strict clients must accept that media type or a matching
  wildcard; `application/json` does not match a distinct `+json` subtype.
- Errors keep their original status. They use RFC 9457 `application/problem+json` by default, or registered
  `application/cbor` when explicitly preferred. Unsupported error preferences fall back to JSON; the unregistered
  `application/problem+cbor` media type is not implemented.
- JSON request bodies accept the base media type or one `charset=utf-8` parameter. CBOR accepts no media parameters;
  both reject ambiguous content fields, content coding other than `identity`, duplicate members, and trailing data.
- `/openapi.json` has a strict JSON-only success representation. `/api-docs` and `/api-redoc` are optional HTML UIs
  that render that same runtime document.

### Pagination

- Opaque cursors are scoped to the operation, effective limit, filters, direction, and position.
- `limit` defaults to 20 and is constrained to 1 through 100. Navigation is exposed only through relative HTTP
  `Link` targets per [RFC 8288](https://www.rfc-editor.org/rfc/rfc8288.html).

### Resource limits

- The three body-bearing operations accept at most exactly 1,000,000 inbound bytes. A valid over-limit declared length
  returns 413 before authentication or content reads. Missing-length and chunked content remains bounded while
  streaming after any protected-route authentication gate and before decoding or persistence.
- GitHub responses are limited to exactly 4 MiB, use an overall ten-second deadline, never retry automatically, and
  follow at most three validated same-origin redirects.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager (the minimum supported version is enforced in both project manifests)
- [just](https://github.com/casey/just) command runner
- Firebase project with Authentication and Firestore enabled when using profile operations
- [Firebase CLI](https://firebase.google.com/docs/cli) for emulators and Functions deployment

## Quick Start

```bash
git clone <repository-url>
cd fastapi-playground
cp .env.example .env
just install        # Install dependencies via uv
just serve          # Start dev server at http://127.0.0.1:8080
```

Public routes and OpenAPI discovery start without Firebase. Set `FIREBASE_PROJECT_ID` and Application Default
Credentials before using the authenticated profile lifecycle.

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
| `ENVIRONMENT` | Runtime mode; `production` enables HSTS and strips 5xx response extensions | `production` |
| `LOG_LEVEL` | Application log verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`) | `INFO` |
| `FIREBASE_PROJECT_ID` | Firebase/GCP project ID | - |
| `FIRESTORE_DATABASE` | Firestore database ID | `(default)` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service account JSON path (local dev) | - |
| `CORS_ORIGINS` | JSON array or comma-separated explicit allowed origins; `*` is rejected | - |

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
.agents/skills/        Six portable project workflows with Codex UI metadata
.github/agents/       Evidence-based security review profile for GitHub Copilot
app/
  main.py              # FastAPI composition, lifespan, and outer ASGI middleware
  dependencies.py      # Typed profile and GitHub dependency injection
  api/                 # API route handlers
    health.py          # Health check endpoint
    hello.py           # Hello greeting endpoints
    items.py           # Items with pagination
    profile.py         # Profile CRUD (Firebase Auth protected)
    github.py          # Public GitHub projections
    openapi_document.py  # Local runtime OpenAPI discovery
  auth/                # Firebase authentication
    firebase.py        # Token verification, FirebaseUser
  core/                # Configuration and infrastructure
    config.py          # Settings class (pydantic-settings)
    logging.py         # Structured JSON logging configuration
    firebase.py        # Firebase Admin SDK and async Firestore client
    content_negotiation.py  # RFC 9110 media-type selection
    openapi.py         # Generated portable OpenAPI projection
    portable_http.py   # Route-bound parsing, negotiation, and query policy
    problems.py        # Stable RFC 9457 errors and handlers
  exceptions/          # Profile domain exceptions
    profile.py         # ProfileNotFoundError, ProfileAlreadyExistsError
  middleware/          # ASGI middleware stack
    body_limit.py      # Request size guard (413 on oversized)
    security.py        # Security headers (HSTS, X-Frame-Options)
  models/              # Pydantic schemas
    error.py           # ProblemResponse schema
    types.py           # Shared types (ContactEmail, PhoneNumber, UTCDateTime)
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
    github_service.py  # Bounded anonymous GitHub client and projection
scripts/
  migrate_profiles.py  # Dry-run-first one-time persisted-profile migration
tests/
  unit/                # Unit tests (mocked dependencies)
  integration/         # API route tests (TestClient)
  e2e/                 # Firebase emulator tests (local only)
  helpers/             # Shared test utilities
functions/             # Firebase Cloud Functions (Python 3.14)
  main.py              # HTTP dad-joke function
  pyproject.toml       # Functions-specific dependencies
  tests/               # Isolated function contract tests
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
| POST | `/v1/hello` | No | Generate a personalized greeting (200 OK) |
| GET | `/v1/items` | No | List items with pagination |
| POST | `/v1/profile` | Yes | Create user profile |
| GET | `/v1/profile` | Yes | Get user profile |
| PATCH | `/v1/profile` | Yes | Update user profile |
| DELETE | `/v1/profile` | Yes | Delete user profile |
| GET | `/v1/github/owners/{owner}` | No | Get a projected public GitHub owner |
| GET | `/v1/github/owners/{owner}/repos` | No | List projected public repositories |
| GET | `/v1/github/repos/{owner}/{repo}` | No | Get a projected public repository |
| GET | `/v1/github/repos/{owner}/{repo}/activity` | No | List projected repository activity |
| GET | `/v1/github/repos/{owner}/{repo}/languages` | No | List projected repository languages |
| GET | `/v1/github/repos/{owner}/{repo}/tags` | No | List projected repository tags |
| GET | `/openapi.json` | No | Retrieve the runtime OpenAPI 3.1 document |
| GET | `/schemas/{Model}.json` | No | Optional standalone JSON Schema extension |

Protected routes require `Authorization: Bearer <Firebase ID token>`. GitHub routes are deliberately anonymous: the
application neither reads an ambient GitHub token nor forwards caller credentials.

## Persisted profile migration

The accepted profile contract retires the persisted `email`, `marketing`, and `terms` keys in favor of
`contact_email`, `marketing_opt_in`, and `terms_accepted`. Before deploying this revision over existing profile data:

1. Quiesce all profile traffic, take a Firestore backup, and keep the retired revision from reading migrated records.
2. Point ADC, `FIREBASE_PROJECT_ID`, and optional `FIRESTORE_DATABASE` at the intended environment.
3. Run `uv run python -m scripts.migrate_profiles` and review `validated`, `pending`, and `written=0`.
4. With separate operational authorization, run `uv run python -m scripts.migrate_profiles --apply`.
5. Rerun the dry run and require `pending=0` before starting the new application revision.
6. Deploy and verify the new revision with a dedicated synthetic principal before restoring profile traffic.

The command validates every document before dispatching writes and compare-checks each document in a transaction. It
also requires canonical-key documents to contain already-canonical values instead of approving values normalized only
in memory. It is dry-run by default and safe to rerun, but Firestore does not make the entire collection migration one
transaction; if a run is interrupted, keep profile traffic quiesced and rerun to completion. Partial adoption becomes
unsafe when the first document is migrated: the retired reader and writer must not serve migrated records. Rollback
requires the backup and retired revision together; do not point the retired revision at forward-migrated data. Do not
run the migration against live data as part of an ordinary code review or test workflow.

The wire cutover is also breaking for generated clients: operation IDs, lower camel case members, item `Money`, error
documents, statuses, representations, and the six GitHub operations changed. Regenerate clients from the new runtime
`/openapi.json` and release them with the server cutover; do not treat the retired and accepted clients as compatible.

## Development

### Build and Test

```bash
just lint               # Check Python style and GitHub Actions security
just typing             # Type-check the FastAPI app
just typing-functions   # Type-check the separate Functions project
just test-functions     # Run isolated Functions tests
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
| `just lint` | Check Ruff linting/formatting and GitHub Actions with zizmor |
| `just typing` | Type checking via ty |
| `just typing-functions` | Type-check the separate Functions project |
| `just test-functions` | Test the separate Functions project |
| `just test` | Unit + integration tests |
| `just test-e2e` | Firebase emulator E2E tests |
| `just test-all` | All test tiers |
| `just cov` | Coverage report (html/json) |
| `just check` | Full app and Functions lint, type, test, and dependency-manifest checks |
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
GIT_SHA="$(git rev-parse HEAD)"
gcloud builds submit --tag "REGION-docker.pkg.dev/PROJECT_ID/REPO/fastapi-playground:${GIT_SHA}"

# Deploy the repository-built standalone image
gcloud run deploy fastapi-playground \
  --image "REGION-docker.pkg.dev/PROJECT_ID/REPO/fastapi-playground:${GIT_SHA}" \
  --platform managed \
  --region REGION
```

The repository Dockerfile produces a standalone image containing the operating system and Python runtime. Do not
combine that image with `--base-image` or `--automatic-updates`: [Cloud Run automatic base image updates](https://cloud.google.com/run/docs/configuring/services/automatic-base-image-updates)
require either a scratch-based application image or a different buildpack source-deployment flow. Adopting either
would change the established build and image convention and requires separate verification. Rebuild the standalone
image to pick up operating-system, Python, and dependency updates.

The image trusts Cloud Run's forwarded proxy headers so application URLs and HTTPS-only security headers reflect the
original client request after Cloud Run terminates TLS. Request logs correlate an incoming valid `traceparent`; the
middleware does not create tracing spans.

For detailed infrastructure setup, see [GCP.md](GCP.md).

### Firebase Cloud Functions

```bash
cd functions
uv venv --python 3.14 venv
uv pip install --python venv/bin/python -r requirements.txt
firebase deploy --only functions --project PROJECT_ID
```

The model-backed function is private. Grant intended callers `roles/run.invoker` on its backing Cloud Run service and
send an ID token when invoking it. The Function deploys in `europe-west4`; its Vertex AI client uses the `global`
endpoint and the auto-updating `gemini-pro-latest` alias. See [functions/README.md](functions/README.md) for the alias
trade-offs and Cloud Functions documentation.

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Description |
|----------|-------------|
| `app-ci.yml` | App and Functions checks, container build, and app test coverage |
| `app-lint.yml` | Fast Ruff linting and formatting feedback |
| `zizmor.yml` | Upload GitHub Actions security findings to code scanning |
| `labeler.yml` | Automatic PR labeling |
| `labeler-manual.yml` | Manual labeling for historical PRs |
| `dependabot-auto-merge.yml` | Auto-merge Dependabot minor/patch updates |

Dependabot is configured in `.github/dependabot.yml` for automated dependency updates.

## Contributing

See [AGENTS.md](AGENTS.md) for coding guidelines and conventions.

## License

MIT - see [LICENSE](LICENSE).
