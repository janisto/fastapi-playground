# Dockerfile for a FastAPI application using uv
FROM python:3.13-slim

# Update system packages to address vulnerabilities.
# RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache

# Run the application.
#CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--port", "8080", "--host", "0.0.0.0"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
