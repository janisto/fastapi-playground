set dotenv-load

PORT := env("PORT", "8080")
ARGS_TEST := env("_UV_RUN_ARGS_TEST", "")
ARGS_SERVE := env("_UV_RUN_ARGS_SERVE", "")

# Container runtime: prefer podman, fallback to docker
CONTAINER_RUNTIME := if `command -v podman 2>/dev/null || true` != "" { "podman" } else { "docker" }


@_:
    just --list

# Start Firebase emulators for E2E tests
[group('test')]
emulators:
    firebase emulators:start --only auth,firestore

# Run all CI-compatible tests (unit + integration)
[group('test')]
test *args:
    uv run {{ ARGS_TEST }} -m pytest tests/unit/ tests/integration/ -v --cov=app {{ args }}

# Run unit tests only
[group('test')]
test-unit *args:
    uv run {{ ARGS_TEST }} -m pytest tests/unit/ -v {{ args }}

# Run integration tests only
[group('test')]
test-integration *args:
    uv run {{ ARGS_TEST }} -m pytest tests/integration/ -v {{ args }}

# Run E2E tests (requires Firebase emulators)
[group('test')]
test-e2e *args:
    uv run {{ ARGS_TEST }} -m pytest tests/e2e/ -v -s {{ args }}

# Run all tests including E2E
[group('test')]
test-all *args:
    uv run {{ ARGS_TEST }} -m pytest tests/ -v --cov=app {{ args }}

# Run tests and measure coverage
[group('test')]
@cov:
    uv run -m coverage erase
    uv run -m pytest tests/unit tests/integration --cov=app --cov-branch --cov-report=term-missing --cov-report=html --cov-report=json:coverage.json

# Run linters and auto-fix issues
[group('qa')]
fix:
    uvx ruff check --fix
    uvx ruff format

# Run linters
[group('qa')]
lint:
    uvx ruff check
    uvx ruff format --check

# Modernize code (PEP 585/604, etc.) via Ruff's pyupgrade
[group('qa')]
modernize:
    uvx ruff check --fix --select UP
    uvx ruff format

# Check types
[group('qa')]
typing:
    uvx ty check

# Quality assurance: fix, format, type check, and test
[group('qa')]
qa: fix typing test

# Perform all checks
[group('qa')]
check: lint typing test

# Run development server
# --no-server-header: Hide server fingerprinting (OWASP recommendation)
[group('run')]
serve:
    uv run {{ ARGS_SERVE }} uvicorn app.main:app --reload --port {{ PORT }} --no-server-header

# Send HTTP request to development server
[group('run')]
req path="" *args:
    @just _http {{ args }} http://127.0.0.1:{{ PORT }}/{{ path }}

_http *args:
    uvx --from httpie http {{ args }}

# Open development server in web browser
[group('run')]
browser:
    uv run -m webbrowser -t http://127.0.0.1:{{ PORT }}


# Container tasks
[group('container')]
container-build image="fastapi-playground:latest" version="dev" runtime_img="":
    {{ CONTAINER_RUNTIME }} build \
        --build-arg VERSION={{ version }} \
        {{ if runtime_img != "" { "--build-arg RUNTIME_IMAGE=" + runtime_img } else { "" } }} \
        -t {{ image }} .

[group('container')]
container-up image="fastapi-playground:latest" name="fastapi-playground" creds="service_account.json":
    {{ CONTAINER_RUNTIME }} run -d --rm --name {{ name }} \
        {{ if path_exists(".env") == "true" { "--env-file .env" } else { "" } }} \
        -p {{ PORT }}:8080 \
        -v "$(pwd)/{{ creds }}:/app/credentials.json:ro" \
        -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
        {{ image }}

[group('container')]
container-logs name="fastapi-playground":
    {{ CONTAINER_RUNTIME }} logs -f {{ name }}

[group('container')]
container-down name="fastapi-playground":
    -{{ CONTAINER_RUNTIME }} stop {{ name }}

# Update dependencies
[group('lifecycle')]
update:
    uv sync --upgrade

# Ensure project virtualenv is up to date
[group('lifecycle')]
install:
    uv sync

# Remove temporary files
[group('lifecycle')]
clean:
    rm -rf .venv .pytest_cache .ruff_cache .coverage htmlcov
    rm -f coverage.json firebase-debug.log
    find . -type d -name "__pycache__" -exec rm -r {} +

# Recreate project virtualenv from nothing
[group('lifecycle')]
fresh: clean install
