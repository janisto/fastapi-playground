"""
Exception handler singleton for fastapi-problem integration.

Provides `eh` for:
1. Registering handlers via add_exception_handler(app, eh)
2. Generating OpenAPI responses via eh.generate_swagger_response()
"""

import uuid
from typing import Any, cast

from fastapi_problem.cors import CorsConfiguration
from fastapi_problem.handler import ExceptionHandler, PostHook, PreHook, StripExtrasPostHook, new_exception_handler
from rfc9457 import Problem
from starlette.requests import Request
from starlette.responses import Response
from starlette_problem.handler import Handler

from app.core.cbor import (
    CBORDecodeError,
    CBORDecodeHTTPException,
    CBORDecodeProblem,
    CBORProblemPostHook,
    UnsupportedMediaTypeHTTPException,
    UnsupportedMediaTypeProblem,
)
from app.core.config import get_settings
from app.core.constants import ERROR_SCHEMA_PATH
from app.core.validation import validation_error_handler
from app.middleware import get_logger
from app.pagination import InvalidCursorError

logger = get_logger(__name__)
settings = get_settings()

REQUEST_ID_HEADER = "X-Request-ID"


def request_id_pre_hook(request: Request, exc: Exception) -> None:
    """
    Ensure request_id is available in request.state for error responses.

    If the middleware hasn't set the request_id (e.g., exception during
    middleware processing), generate one to ensure all error responses
    have a request ID.
    """
    if not hasattr(request.state, "request_id"):
        request.state.request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())


def request_id_post_hook(
    content: dict[str, Any],
    request: Request,
    response: Response,
) -> tuple[dict[str, Any], Response]:
    """
    Add X-Request-ID header to error response.

    Ensures error responses include the request ID for client traceability.
    """
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        response.headers[REQUEST_ID_HEADER] = request_id
    return content, response


def strip_about_blank_type_post_hook(
    content: dict[str, Any],
    request: Request,
    response: Response,
) -> tuple[dict[str, Any], Response]:
    """
    Remove 'type' field when it equals 'about:blank'.

    Per RFC 9457, when 'type' is not present its value is assumed to be
    'about:blank'. Omitting it reduces response size.
    """
    if content.get("type") != "about:blank":
        return content, response

    content.pop("type", None)
    response.body = response.render(content)
    response.headers["content-length"] = str(len(response.body))
    return content, response


def schema_link_post_hook(
    content: dict[str, Any],
    request: Request,
    response: Response,
) -> tuple[dict[str, Any], Response]:
    """
    Add $schema field and Link header to all RFC 9457 error responses.

    Per JSON Schema spec, $schema declares which schema the document conforms to.
    This enables client-side validation and tooling support (e.g., IDE completion).
    The Link header with rel="describedBy" provides discoverability per RFC 8288.

    Note: $schema must be an absolute URI per JSON Schema specification.
    """
    # Only add $schema if not already present (custom handlers may set their own)
    if "$schema" not in content:
        schema_url = str(request.base_url).rstrip("/") + ERROR_SCHEMA_PATH
        content["$schema"] = schema_url
        response.body = response.render(content)
        response.headers["content-length"] = str(len(response.body))

    # Add Link header for discoverability (RFC 8288)
    response.headers["Link"] = f'<{ERROR_SCHEMA_PATH}>; rel="describedBy"'

    return content, response


def cbor_decode_error_handler(
    eh: ExceptionHandler,
    request: Request,
    exc: CBORDecodeError,
) -> CBORDecodeProblem:
    """Handle CBOR decode errors with RFC 9457 Problem Details."""
    return CBORDecodeProblem(detail=exc.detail)


def cbor_decode_http_exception_handler(
    eh: ExceptionHandler,
    request: Request,
    exc: CBORDecodeHTTPException,
) -> CBORDecodeProblem:
    """Handle CBOR decode HTTPException with RFC 9457 Problem Details."""
    return CBORDecodeProblem(detail=str(exc.detail))


def unsupported_media_type_handler(
    eh: ExceptionHandler,
    request: Request,
    exc: UnsupportedMediaTypeHTTPException,
) -> UnsupportedMediaTypeProblem:
    """Handle unsupported media type with RFC 9457 Problem Details."""
    return UnsupportedMediaTypeProblem(detail=str(exc.detail))


def invalid_cursor_error_handler(
    eh: ExceptionHandler,
    request: Request,
    exc: InvalidCursorError,
) -> Problem:
    """
    Handle invalid pagination cursor with RFC 9457 Problem Details.

    Returns 400 Bad Request per HTTP semantics: an invalid cursor is a
    malformed request parameter, not a schema validation error (422).
    """
    schema_url = str(request.base_url).rstrip("/") + ERROR_SCHEMA_PATH
    extras: dict[str, Any] = {"$schema": schema_url}
    return Problem(
        title="Bad Request",
        detail=str(exc) or "invalid cursor format",
        status=400,
        **extras,
    )


# Per CORS spec, credentials cannot be used with wildcard origin
# Derive allow_credentials the same way as in main.py for consistency
cors_config = (
    CorsConfiguration(
        allow_origins=settings.cors_origins,
        allow_methods=settings.cors_methods,
        allow_headers=settings.cors_headers,
        allow_credentials="*" not in settings.cors_origins,
    )
    if settings.cors_origins
    else None
)

eh = new_exception_handler(
    logger=logger,
    strict_rfc9457=True,
    documentation_uri_template="about:blank",
    request_validation_handler=validation_error_handler,
    cors=cors_config,
    handlers={
        CBORDecodeError: cast("Handler", cbor_decode_error_handler),
        CBORDecodeHTTPException: cast("Handler", cbor_decode_http_exception_handler),
        UnsupportedMediaTypeHTTPException: cast("Handler", unsupported_media_type_handler),
        InvalidCursorError: cast("Handler", invalid_cursor_error_handler),
    },
    pre_hooks=[
        cast("PreHook", request_id_pre_hook),
    ],
    post_hooks=[
        cast("PostHook", request_id_post_hook),
        cast("PostHook", strip_about_blank_type_post_hook),
        cast("PostHook", schema_link_post_hook),
        cast(
            "PostHook",
            StripExtrasPostHook(
                mandatory_fields=["$schema", "title", "status", "detail", "errors"],
                include_status_codes=[500, 502, 503, 504],
                enabled=settings.environment == "production",
                logger=logger,
            ),
        ),
        cast("PostHook", CBORProblemPostHook()),
    ],
)
