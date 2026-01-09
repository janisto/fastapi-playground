"""
FastAPI application with Firebase Authentication and Firestore integration.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_problem.handler import add_exception_handler

from app.api import health, schemas, v1_router
from app.api.schemas import populate_schema_cache
from app.core.config import get_settings
from app.core.exception_handler import eh
from app.core.firebase import close_async_firestore_client, initialize_firebase
from app.middleware import (
    BodySizeLimitMiddleware,
    RequestContextLogMiddleware,
    SecurityHeadersMiddleware,
    setup_logging,
)


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
    redirect_slashes=False,
    lifespan=lifespan,
)

# Include routers
app.include_router(v1_router)  # /v1/profile, /v1/hello, /v1/items
app.include_router(health.router)  # /health (unversioned)
app.include_router(schemas.router)  # /schemas (unversioned)

# Populate schema cache from OpenAPI spec (must be after all routers are registered)
populate_schema_cache(app.openapi())

# Register RFC 9457 Problem Details exception handler
add_exception_handler(app, eh)

# Middleware order: last added = outermost (first to run on request, last on response)
# Desired request flow: Logging → Security → BodyLimit → CORS → route
# Desired response flow: route → CORS → BodyLimit → Security → Logging

# CORS (innermost) - handles preflight and adds CORS headers early in response
settings = get_settings()
if settings.cors_origins:  # pragma: no cover
    # Per CORS spec, credentials cannot be used with wildcard origin
    allow_credentials = "*" not in settings.cors_origins
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
        expose_headers=settings.cors_expose_headers,
    )

# Body size limit - reject oversized requests before further processing
app.add_middleware(BodySizeLimitMiddleware)  # type: ignore[arg-type]

# Security headers - add security headers to all responses
app.add_middleware(
    SecurityHeadersMiddleware,  # type: ignore[arg-type]
    hsts=True,
    hsts_include_subdomains=True,
    hsts_preload=False,
)

# Logging (outermost) - capture full request lifecycle including all middleware
app.add_middleware(RequestContextLogMiddleware)  # type: ignore[arg-type]
