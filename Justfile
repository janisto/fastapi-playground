set dotenv-load

PORT := env("PORT", "8080")
ARGS_TEST := env("_UV_RUN_ARGS_TEST", "")
ARGS_SERVE := env("_UV_RUN_ARGS_SERVE", "")


@_:
    just --list


# Run tests
[group('qa')]
test *args:
    uv run {{ ARGS_TEST }} -m pytest {{ args }}

_cov *args:
    uv run -m coverage {{ args }}

# Run tests and measure coverage
[group('qa')]
@cov:
    just _cov erase
    just _cov run -m pytest tests
    just _cov combine
    just _cov report
    just _cov html
    just _cov json -o coverage.json

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
docker-run image="fastapi-playground:local" env_file=".env" name="fastapi-playground":
    docker run --rm --name {{ name }} -p {{ PORT }}:8080 --env-file {{ env_file }} {{ image }}

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
