# syntax=docker/dockerfile:1.17.0
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
# Tip: for smaller images, consider python:3.13-alpine, python:3.13-slim, python:3.13-slim-bookworm or python:3.13-slim-bullseye
ARG PYTHON_IMAGE=python:3.13-slim
FROM ${PYTHON_IMAGE} AS builder

# Update system packages to address vulnerabilities.
# RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install dependencies into a project venv using only lockfile
WORKDIR /app
COPY uv.lock pyproject.toml ./
RUN uv sync --frozen --no-dev --no-cache

# Copy only application source (avoid tests, docs, etc.)
COPY app ./app

# Prune caches/bytecode to slim the venv
RUN find .venv -type d -name '__pycache__' -prune -exec rm -rf {} + \
	&& find .venv -type f -name '*.pyc' -delete

# Final runtime stage (same base by default; can be swapped via --build-arg)
FROM ${PYTHON_IMAGE} AS runtime

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
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app

# Cloud Run expects the server to listen on $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
