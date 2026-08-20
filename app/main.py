"""
FastAPI application with Firebase Authentication and Firestore integration.
"""

import logging
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast, override

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi_request_observability import (
    AccessLogConfig,
    AccessLogMiddleware,
    LoggingPreset,
    RequestContextConfig,
    RequestContextMiddleware,
    TraceContextLevel,
)
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, ExceptionHandler

from app.api import business_routers, health, openapi_document, schemas
from app.api.schemas import populate_schema_cache
from app.core.config import Settings, get_settings
from app.core.firebase import close_async_firestore_client
from app.core.logging import configure_logging
from app.core.openapi import build_openapi_document
from app.core.problems import (
    PortableProblem,
    http_exception_handler,
    portable_problem_handler,
    request_validation_handler,
    unhandled_exception_handler,
)
from app.middleware import (
    BodySizeLimitMiddleware,
    SecurityHeadersMiddleware,
)

_TRACE_CONTEXT_LEVEL = TraceContextLevel.LEVEL_1
_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


def _validate_request_id(value: str) -> bool:
    return _REQUEST_ID.fullmatch(value) is not None


class PortableFastAPI(FastAPI):
    """FastAPI application whose generated document is the portable projection."""

    @override
    def openapi(self) -> dict[str, Any]:
        return build_openapi_document(self)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan manager.
    """
    # Startup
    configure_logging()
    try:
        yield
    finally:
        close_async_firestore_client()


# Create the FastAPI application before wrapping it with response-wide ASGI middleware.
fastapi_app = PortableFastAPI(
    title="FastAPI Playground",
    description="A FastAPI application with Firebase Authentication and Firestore",
    version="0.1.0",
    docs_url="/api-docs",
    redoc_url="/api-redoc",
    openapi_url=None,
    redirect_slashes=False,
    lifespan=lifespan,
)


@fastapi_app.get("/api-docs", include_in_schema=False, response_class=HTMLResponse)
async def swagger_ui() -> HTMLResponse:
    """Render Swagger UI against the strict runtime OpenAPI route."""
    return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{fastapi_app.title} - Swagger UI")


@fastapi_app.get("/api-redoc", include_in_schema=False, response_class=HTMLResponse)
async def redoc_ui() -> HTMLResponse:
    """Render ReDoc against the strict runtime OpenAPI route."""
    return get_redoc_html(openapi_url="/openapi.json", title=f"{fastapi_app.title} - ReDoc")


# Include routers
for business_router in business_routers:
    fastapi_app.include_router(business_router)
fastapi_app.include_router(health.router)  # /health (unversioned)
fastapi_app.include_router(openapi_document.router)
fastapi_app.include_router(schemas.router)  # /schemas (unversioned)

populate_schema_cache(fastapi_app.openapi())

fastapi_app.add_exception_handler(PortableProblem, cast("ExceptionHandler", portable_problem_handler))
fastapi_app.add_exception_handler(RequestValidationError, cast("ExceptionHandler", request_validation_handler))
fastapi_app.add_exception_handler(StarletteHTTPException, cast("ExceptionHandler", http_exception_handler))
fastapi_app.add_exception_handler(Exception, cast("ExceptionHandler", unhandled_exception_handler))


def _build_application(inner_app: ASGIApp, application_settings: Settings) -> RequestContextMiddleware:
    """
    Compose the response-wide middleware stack from explicit settings.
    """
    application: ASGIApp = BodySizeLimitMiddleware(inner_app)

    # CORS wraps the body limit and FastAPI recovery so preflights and error responses retain CORS headers.
    if application_settings.cors_origins:
        application = CORSMiddleware(
            application,
            allow_origins=application_settings.cors_origins,
            allow_credentials=True,
            allow_methods=application_settings.cors_methods,
            allow_headers=application_settings.cors_headers,
            expose_headers=application_settings.cors_expose_headers,
        )

    access_log = AccessLogMiddleware(
        application,
        config=AccessLogConfig(
            logger=logging.getLogger("http.access"),
            preset=LoggingPreset.GCP,
            trace_context_level=_TRACE_CONTEXT_LEVEL,
            capture_path=False,
            capture_peer_ip=False,
            capture_user_agent=False,
            capture_error=False,
        ),
    )
    security_headers = SecurityHeadersMiddleware(
        access_log,
        hsts=application_settings.is_production,
        hsts_include_subdomains=True,
        hsts_preload=False,
    )

    # Request context remains outermost so every final response receives X-Request-ID.
    return RequestContextMiddleware(
        security_headers,
        config=RequestContextConfig(
            trace_context_level=_TRACE_CONTEXT_LEVEL,
            request_id_validator=_validate_request_id,
        ),
    )


settings = get_settings()
app = _build_application(fastapi_app, settings)
security_headers_middleware = cast("SecurityHeadersMiddleware", app.app)
access_log_middleware = cast("AccessLogMiddleware", security_headers_middleware.app)
