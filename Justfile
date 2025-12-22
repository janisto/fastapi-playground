set dotenv-load

PORT := env("PORT", "8080")
ARGS_TEST := env("_UV_RUN_ARGS_TEST", "")
ARGS_SERVE := env("_UV_RUN_ARGS_SERVE", "")


@_:
    just --list


# Run all CI-compatible tests (unit + integration)
[group('qa')]
test *args:
    uv run {{ ARGS_TEST }} -m pytest tests/unit/ tests/integration/ -v --cov=app {{ args }}

# Run unit tests only
[group('qa')]
test-unit *args:
    uv run {{ ARGS_TEST }} -m pytest tests/unit/ -v {{ args }}

# Run integration tests only
[group('qa')]
test-integration *args:
    uv run {{ ARGS_TEST }} -m pytest tests/integration/ -v {{ args }}

# Run E2E tests (requires Firebase emulators)
[group('qa')]
test-e2e *args:
    uv run {{ ARGS_TEST }} -m pytest tests/e2e/ -v -s {{ args }}

# Run all tests including E2E
[group('qa')]
test-all *args:
    uv run {{ ARGS_TEST }} -m pytest tests/ -v --cov=app {{ args }}

# Run tests and measure coverage
[group('qa')]
@cov:
    uv run -m coverage erase
    uv run -m pytest tests/unit tests/integration --cov=app --cov-branch --cov-report=term-missing --cov-report=html --cov-report=json:coverage.json

# Run linters
[group('qa')]
lint:
    uvx ruff check
    uvx ruff format

# Modernize code (PEP 585/604, etc.) via Ruff's pyupgrade
[group('qa')]
modernize:
    uvx ruff check --fix --select UP
    uvx ruff format

# Check types
[group('qa')]
typing:
    uvx ty check --python .venv app

# Perform all checks
[group('qa')]
check-all: lint typing test

# Run development server
[group('run')]
serve:
    uv run {{ ARGS_SERVE }} -m fastapi dev app/main.py --port {{ PORT }}

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
docker-build image="fastapi-playground:local" pyimg="":
        if [ -n "{{ pyimg }}" ]; then \
            docker build --build-arg PYTHON_IMAGE={{ pyimg }} -t {{ image }} . ;\
        else \
            docker build -t {{ image }} . ;\
        fi

[group('container')]
docker-run image="fastapi-playground:local" env_file=".env" name="fastapi-playground" creds="service_account.json":
    docker run --rm --name {{ name }} -p {{ PORT }}:8080 \
        --env-file {{ env_file }} \
        -v "$(pwd)/{{ creds }}:/app/credentials.json:ro" \
        -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
        {{ image }}

[group('container')]
docker-logs name="fastapi-playground":
    docker logs -f {{ name }}


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
    find . -type d -name "__pycache__" -exec rm -r {} +

# Recreate project virtualenv from nothing
[group('lifecycle')]
fresh: clean install


# Start Firebase emulators for E2E tests
[group('run')]
emulators:
    firebase emulators:start --only auth,firestore
