"""
FastAPI application with Firebase Authentication and Firestore integration.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_problem.handler import add_exception_handler
from fastapi_request_observability import (
    AccessLogConfig,
    AccessLogMiddleware,
    LoggingPreset,
    RequestContextMiddleware,
)
from starlette.types import ASGIApp

from app.api import business_routers, health, schemas
from app.api.schemas import populate_schema_cache
from app.core.config import get_settings
from app.core.exception_handler import exception_handler
from app.core.firebase import close_async_firestore_client, initialize_firebase
from app.core.logging import configure_logging
from app.core.openapi import register_schema_components
from app.middleware import (
    BodySizeLimitMiddleware,
    SecurityHeadersMiddleware,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan manager.
    """
    # Startup
    configure_logging()
    initialize_firebase()

    try:
        yield
    finally:
        close_async_firestore_client()


# Create the FastAPI application before wrapping it with response-wide ASGI middleware.
fastapi_app = FastAPI(
    title="FastAPI Playground",
    description="A FastAPI application with Firebase Authentication and Firestore",
    version="0.1.0",
    docs_url="/api-docs",
    redoc_url="/api-redoc",
    redirect_slashes=False,
    lifespan=lifespan,
)

# Include routers
for business_router in business_routers:
    fastapi_app.include_router(business_router)
fastapi_app.include_router(health.router)  # /health (unversioned)
fastapi_app.include_router(schemas.router)  # /schemas (unversioned)

# Populate schema cache from OpenAPI spec (must be after all routers are registered)
openapi_schema = fastapi_app.openapi()
register_schema_components(openapi_schema)
populate_schema_cache(openapi_schema)

# Register RFC 9457 Problem Details exception handler
add_exception_handler(fastapi_app, exception_handler)

settings = get_settings()
application: ASGIApp = BodySizeLimitMiddleware(fastapi_app)

# CORS wraps the body limit and FastAPI recovery so preflights and error responses retain CORS headers.
if settings.cors_origins:  # pragma: no cover
    allow_credentials = "*" not in settings.cors_origins
    application = CORSMiddleware(
        application,
        allow_origins=settings.cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
        expose_headers=settings.cors_expose_headers,
    )

access_log_middleware = AccessLogMiddleware(
    application,
    config=AccessLogConfig(
        logger=logging.getLogger("http.access"),
        preset=LoggingPreset.GCP,
    ),
)
security_headers_middleware = SecurityHeadersMiddleware(
    access_log_middleware,
    hsts=settings.is_production,
    hsts_include_subdomains=True,
    hsts_preload=False,
)

# Request context remains outermost so every final response receives X-Request-ID.
app = RequestContextMiddleware(security_headers_middleware)
