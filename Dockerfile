# syntax=docker/dockerfile:1.19.0
# Dockerfile for a FastAPI application using uv
#
# Cloud Run automatic base image updates:
# - Build your app image as usual.
# - Deploy with: gcloud run deploy SERVICE \
#     --image YOUR_IMAGE \
#     --base-image BASE_IMAGE \
#     --automatic-updates
#   This links your app image to a managed base so Google can patch it without a new revision.
#
# Tip: for smaller images, consider python:3.14-alpine, python:3.14-slim, python:3.14-slim-trixie, python:3.14-slim-bookworm or python:3.14-slim-bullseye
ARG PYTHON_IMAGE=python:3.14-slim-trixie
FROM ${PYTHON_IMAGE} AS builder

# Update system packages and install runtime dependencies
# libmagic1: required by python-magic for file type detection
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Enable bytecode compilation, to improve cold-start performance.
ENV UV_COMPILE_BYTECODE=1

# Disable installer metadata, to create a deterministic layer.
ENV UV_NO_INSTALLER_METADATA=1

# Enable copy mode to support bind mount caching.
ENV UV_LINK_MODE=copy

# Install dependencies into a project venv using only lockfile
WORKDIR /app
COPY uv.lock pyproject.toml ./
RUN uv sync --frozen --no-dev --no-cache

# Copy only application source (avoid tests, docs, etc.)
COPY app ./app

# Final runtime stage (same base by default; can be swapped via --build-arg)
FROM ${PYTHON_IMAGE} AS runtime

# Install runtime dependencies
# libmagic1: required by python-magic for file type detection
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --system --gid 1001 app \
    && useradd --system --gid 1001 --uid 1001 --create-home app

# OCI provenance label for base image (useful for tooling/visibility)
ARG PYTHON_IMAGE
LABEL org.opencontainers.image.base.name="${PYTHON_IMAGE}"

# Ensure we use the project virtualenv at runtime
ENV VIRTUAL_ENV=/app/.venv \
	PATH=/app/.venv/bin:$PATH \
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

# Copy only what is needed to run
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/app /app/app

# Switch to non-root user
USER app

# Cloud Run expects the server to listen on $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Run the application (exec form with sh -c for proper signal handling and $PORT expansion)
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
