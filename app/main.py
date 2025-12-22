"""
FastAPI application with Firebase Authentication and Firestore integration.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.firebase import close_async_firestore_client, initialize_firebase
from app.core.handlers import register_exception_handlers
from app.middleware import (
    BodySizeLimitMiddleware,
    RequestContextLogMiddleware,
    SecurityHeadersMiddleware,
    setup_logging,
)
from app.routers import health, profile


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan manager.
    """
    # Startup
    setup_logging()
    initialize_firebase()

    yield

    # Shutdown
    await close_async_firestore_client()


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
app.include_router(profile.router)
app.include_router(health.router)

# Register exception handlers
register_exception_handlers(app)

# Middleware order: last added = outermost (first to run on request, last on response)
# Desired request flow: Logging → Security → BodyLimit → CORS → route
# Desired response flow: route → CORS → BodyLimit → Security → Logging

# CORS (innermost) - handles preflight and adds CORS headers early in response
settings = get_settings()
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Cloud-Trace-Context"],
    )

# Body size limit - reject oversized requests before further processing
app.add_middleware(BodySizeLimitMiddleware)

# Security headers - add security headers to all responses
app.add_middleware(
    SecurityHeadersMiddleware,
    hsts=True,
    hsts_include_subdomains=True,
    hsts_preload=False,
    x_frame_options="DENY",
    referrer_policy="same-origin",
)

# Logging (outermost) - capture full request lifecycle including all middleware
app.add_middleware(RequestContextLogMiddleware)


@app.get("/", tags=["root"], include_in_schema=False)
async def root() -> dict[str, str]:
    """
    Root endpoint.
    """
    return {"message": "Hello", "docs": "/api-docs"}
