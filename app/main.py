"""
FastAPI application with Firebase Authentication and Firestore integration.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.body_limit import BodySizeLimitMiddleware
from app.core.config import get_settings
from app.core.firebase import initialize_firebase
from app.core.logging import RequestContextLogMiddleware, setup_logging
from app.core.security import SecurityHeadersMiddleware
from app.models.health import HealthResponse
from app.routers import dog, profile


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager."""
    # Initialize services
    setup_logging()
    initialize_firebase()

    yield


# Create FastAPI app with API documentation
app = FastAPI(
    title="FastAPI Playground",
    description="A FastAPI application with Firebase Authentication and Firestore",
    version="0.1.0",
    docs_url="/api-docs",
    redoc_url="/api-redoc",
    lifespan=lifespan,
)

# Include routers
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(dog.router, prefix="/dogs", tags=["dogs"])

# Add logging middleware to capture trace context
app.add_middleware(RequestContextLogMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(
    SecurityHeadersMiddleware,
    hsts=True,
    hsts_include_subdomains=True,
    hsts_preload=False,
    x_frame_options="DENY",
    referrer_policy="same-origin",
)

# CORS with strict allowlist
settings = get_settings()
allowed_origins = []  # override via env if needed
try:
    # Expect comma-separated origins in CORS_ORIGINS env
    raw = getattr(settings, "cors_origins", None)  # may not exist yet
    if isinstance(raw, str) and raw.strip():
        allowed_origins = [o.strip() for o in raw.split(",") if o.strip()]
except Exception:
    allowed_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/", tags=["root"], include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Hello World", "docs": "/api-docs"}


@app.get(
    "/health",
    tags=["health"],
    summary="Service health",
    description="Lightweight health probe for liveness checks.",
    operation_id="health_get",
    responses={
        200: {
            "description": "Service is healthy",
            "content": {"application/json": {"example": {"status": "healthy"}}},
        }
    },
)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")
