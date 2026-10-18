# FastAPI Playground

[![CI](https://img.shields.io/github/actions/workflow/status/janisto/fastapi-playground/app-ci.yml?branch=main&label=CI)](https://github.com/janisto/fastapi-playground/actions/workflows/app-ci.yml)
[![Lint](https://img.shields.io/github/actions/workflow/status/janisto/fastapi-playground/app-lint.yml?branch=main&label=lint)](https://github.com/janisto/fastapi-playground/actions/workflows/app-lint.yml)
[![Python 3.15+](https://img.shields.io/badge/python-3.15%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/github/license/janisto/fastapi-playground)](LICENSE)

A FastAPI reference application for the accepted portable playground API. It demonstrates strict JSON and CBOR
contracts, Firebase-authenticated Firestore profile lifecycle operations, a credential-free GitHub REST projection,
and a modern Python workflow using `uv` and `just`.

This example is not deployed. GCP is a possible future deployment target; pushes, pull requests, and merges run CI
only. The [deployment instructions](GCP.md) describe optional manual setup in a project you control.

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

- Python 3.15+ (the local environment and container use 3.15.0)
- [uv](https://docs.astral.sh/uv/) package manager (the minimum supported version is enforced in both project manifests)
- [just](https://github.com/casey/just) 1.59.0 command runner
- [actionlint](https://github.com/rhysd/actionlint) 1.7.12 for local workflow validation
- Node.js 24 LTS and `npx` only when running Firebase tooling
- [Firebase CLI](https://firebase.google.com/docs/cli) 15.34.0, selected by `just emulators`, for local Auth and Firestore emulators
- A project you control with Authentication and Firestore enabled when using hosted profile operations

## Quick Start

```bash
git clone <repository-url>
cd fastapi-playground
cp .env.example .env
just install        # Install dependencies via uv
just serve          # Start dev server at http://127.0.0.1:8080
```

Public routes, OpenAPI discovery, and unit/integration tests require no GCP account. For local Firestore E2E tests,
run `just emulators` and `just test-e2e`; both use the synthetic `demo-test` project. Hosted profile operations require
`FIREBASE_PROJECT_ID` and Application Default Credentials for your own project.

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

Cloud MCP connections are optional and are not configured by the repository. See
[GCP.md](GCP.md#optional-local-mcp-connections) for Firebase and Cloud Logging configuration, IAM, authentication, and
token refresh. Personal `.vscode/mcp.json`, `.codex/config.toml`, and `.firebaserc` files are ignored by Git.

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
    recovery.py        # Contains post-response FastAPI exception re-raises
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
    profile/           # ProfileService and Firestore-safe principal keys
    github_service.py  # Bounded anonymous GitHub client and projection
tests/
  unit/                # Unit tests (mocked dependencies)
  integration/         # API route tests (TestClient)
  e2e/                 # Firebase emulator tests (local only)
  helpers/             # Shared test utilities
functions/             # Firebase Cloud Functions (Python 3.15)
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

## Development

### Build and Test

```bash
just lint               # Check Python style
just workflow-check     # Check GitHub Actions syntax and security
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
| `just lint` | Check Ruff linting and formatting |
| `just workflow-check` | Check GitHub Actions with actionlint 1.7.12 and locked, pedantic offline zizmor |
| `just typing` | Type checking via ty |
| `just typing-functions` | Type-check the separate Functions project |
| `just test-functions` | Test the separate Functions project |
| `just test` | Unit + integration tests |
| `just test-e2e` | Firebase emulator E2E tests |
| `just test-all` | All test tiers |
| `just cov` | Coverage report (html/json) |
| `just check` | Workflow, app and Functions lint, type, test, and dependency-manifest checks |
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

Public container routes require no credentials. Profile requests require Application Default Credentials or a
service-account credential mounted into the container. Credential mounting is explicit; pass an existing absolute or
repository-relative file as the third positional argument:

```bash
just container-up fastapi-playground:latest fastapi-playground service_account.json
```

An invalid credential path fails before starting the container.

## Deployment

These commands are optional manual actions for your own project. Complete the prerequisites in [GCP.md](GCP.md)
first; CI only validates the examples and builds a local container image.

### Google Cloud Run

```bash
# Build and push to Artifact Registry
GIT_SHA="$(git rev-parse HEAD)"
gcloud builds submit --project PROJECT_ID \
  --tag "REGION-docker.pkg.dev/PROJECT_ID/REPO/fastapi-playground:${GIT_SHA}"

# Deploy the repository-built standalone image
gcloud run deploy fastapi-playground \
  --project PROJECT_ID \
  --image "REGION-docker.pkg.dev/PROJECT_ID/REPO/fastapi-playground:${GIT_SHA}" \
  --platform managed \
  --region REGION \
  --service-account RUNTIME_SERVICE_ACCOUNT \
  --set-env-vars FIREBASE_PROJECT_ID=PROJECT_ID,ENVIRONMENT=production,LOG_LEVEL=INFO \
  --allow-unauthenticated
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

Python 3.15 is the local target, including `python315` in `firebase.json`. As of 2026-10-17, Google's published Functions
runtimes and Firebase CLI 15.34.0 do not support it. These commands are retained for future use after support lands;
deployment and Functions emulation are currently blocked. Recheck the [platform runtime table](https://docs.cloud.google.com/functions/docs/runtime-support#python) and
Firebase CLI support before using the [Functions instructions](functions/README.md).

```bash
cd functions
uv venv --python 3.15 venv
uv pip install --python venv/bin/python -r requirements.txt
firebase deploy --only functions --project PROJECT_ID
```

The model-backed function is private. Grant intended callers `roles/run.invoker` on its backing Cloud Run service and
send an ID token when invoking it. The Function deploys in `europe-west4`; its Vertex AI client uses the `global`
endpoint and the auto-updating `gemini-pro-latest` alias. See [functions/README.md](functions/README.md) for the alias
trade-offs and Cloud Functions documentation.

## CI

GitHub Actions workflows in `.github/workflows/` validate code and maintain the repository. They do not publish
container images or deploy cloud resources.

| Workflow | Description |
|----------|-------------|
| `app-ci.yml` | Python quality, independent actionlint/zizmor checks, gated tests and container runtime smoke, and required `ci` result |
| `app-lint.yml` | Fast Ruff linting and formatting feedback |
| `labeler.yml` | Automatic PR labeling |
| `labeler-manual.yml` | Manual labeling for historical PRs |
| `dependabot-auto-merge.yml` | Auto-merge Dependabot minor/patch updates |

Validation runs on pull requests to any base branch, including higher stack layers, and pushes to `main`. The required
`ci` check rejects failed, cancelled, or unexpectedly skipped jobs; the separate required `lint` check remains intact.
Local and CI scans use actionlint 1.7.12 and zizmor 1.31.1 with the pedantic persona and offline audits. CI uses the
official actionlint image, which also bundles ShellCheck and Pyflakes; local actionlint uses those tools when installed.
Zizmor runs once in enforcing plain mode for every validation event, including fork and Dependabot PRs. Findings fail
the required `ci` check. Coverage reports remain downloadable after test or threshold failures when coverage ran.
Container validation checks Python 3.15.0, the non-root runtime user, credential-free startup, the health response, and
graceful shutdown.

Dependabot is configured in `.github/dependabot.yml` for quarterly updates with a one-day cooldown. Standalone tool
pins must be reviewed separately when modernizing. Dependabot security alerts and automated security updates are
disabled; scheduled version updates remain configured. GitHub's graph updater rejected Python 3.15 on 2026-10-18
because its supported runtime list ended at Python 3.14. Keep the Python 3.15 target and use `just update` for native
dependency upgrades while that upstream limitation remains. Disabled alerts do not establish that dependencies are
free of vulnerabilities.

Ruff and ty are excluded from Dependabot version updates and auto-merge. Their patch releases can change diagnostics,
configuration, and fixes, so agents upgrade them separately with release-note review, configuration adjustments, and
the full quality gate. Other eligible dependency updates retain their automatic path.

## Contributing

See [AGENTS.md](AGENTS.md) for coding guidelines and conventions.

## License

MIT - see [LICENSE](LICENSE).
