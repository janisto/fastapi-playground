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

ARG PYTHON_IMAGE=python:3.13-slim
FROM ${PYTHON_IMAGE} AS builder

# Update system packages to address vulnerabilities.
# RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the image and install dependencies (locked)
WORKDIR /app
COPY . /app
RUN uv sync --frozen --no-cache

# Final runtime stage (same base by default; can be swapped via --build-arg)
FROM ${PYTHON_IMAGE} AS runtime

# OCI provenance label for base image (useful for tooling/visibility)
LABEL org.opencontainers.image.base.name="${PYTHON_IMAGE}"

# Copy built app and .venv from builder
COPY --from=builder /app /app
WORKDIR /app

# Cloud Run expects the server to listen on $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
