# syntax=docker/dockerfile:1.19.0
# Dockerfile for a FastAPI application using uv
#
# Uses ghcr.io/astral-sh/uv images which include both Python and uv pre-installed.
# See: https://docs.astral.sh/uv/guides/integration/docker/
# Example: https://github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile
#
# Cloud Run automatic base image updates:
# - Build your app image as usual.
# - Deploy with: gcloud run deploy SERVICE \
#     --image YOUR_IMAGE \
#     --base-image BASE_IMAGE \
#     --automatic-updates
#   This links your app image to a managed base so Google can patch it without a new revision.

# Builder image: includes uv for dependency management
ARG UV_IMAGE=ghcr.io/astral-sh/uv:python3.14-trixie-slim
# Runtime image: minimal Python image without uv (not needed at runtime)
ARG PYTHON_IMAGE=python:3.14-slim-trixie

FROM ${UV_IMAGE} AS builder

# Install runtime dependencies
# libmagic1: required by python-magic for file type detection
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation to improve cold-start performance
ENV UV_COMPILE_BYTECODE=1

# Disable installer metadata to create a deterministic build
ENV UV_NO_INSTALLER_METADATA=1

# Enable copy mode to support bind mount caching
ENV UV_LINK_MODE=copy

# Disable Python downloads since Python is already in the base image
ENV UV_PYTHON_DOWNLOADS=0

# Omit development dependencies
ENV UV_NO_DEV=1

# Use frozen lockfile for reproducible builds
ENV UV_FROZEN=1

WORKDIR /app

# Install dependencies first (better layer caching)
# Uses bind mounts for lockfile and cache mount for uv cache
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-install-project

# Copy application source and project files, then sync to install the project
COPY pyproject.toml uv.lock ./
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-editable

# Runtime stage: uses minimal Python image (no uv needed at runtime)
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
