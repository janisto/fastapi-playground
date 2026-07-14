"""
Exception handler singleton for fastapi-problem integration.

Provides `exception_handler` for registering handlers with the FastAPI application.
"""

import logging
from typing import Any, cast

from fastapi_problem.handler import ExceptionHandler, PostHook, StripExtrasPostHook, new_exception_handler
from rfc9457 import Problem
from starlette.requests import Request
from starlette.responses import Response
from starlette_problem.handler import Handler

from app.core.cbor import (
    CBORDecodeError,
    CBORDecodeHTTPException,
    CBORDecodeProblem,
    CBORProblemPostHook,
    NotAcceptableHTTPException,
    NotAcceptableProblem,
    UnsupportedMediaTypeHTTPException,
    UnsupportedMediaTypeProblem,
)
from app.core.config import get_settings
from app.core.constants import PROBLEM_SCHEMA_PATH, VALIDATION_PROBLEM_SCHEMA_PATH
from app.core.schema_links import build_described_by_link
from app.core.validation import validation_error_handler
from app.pagination import InvalidCursorError

logger = logging.getLogger(__name__)
settings = get_settings()


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
    Add a schema-discovery Link header to all RFC 9457 error responses.
    """
    schema_path = VALIDATION_PROBLEM_SCHEMA_PATH if "errors" in content else PROBLEM_SCHEMA_PATH

    response.headers["Link"] = build_described_by_link(schema_path)

    return content, response


def cbor_decode_error_handler(
    exception_handler: ExceptionHandler,
    request: Request,
    exc: CBORDecodeError,
) -> CBORDecodeProblem:
    """
    Handle CBOR decode errors with RFC 9457 Problem Details.
    """
    return CBORDecodeProblem(detail=exc.detail)


def cbor_decode_http_exception_handler(
    exception_handler: ExceptionHandler,
    request: Request,
    exc: CBORDecodeHTTPException,
) -> CBORDecodeProblem:
    """
    Handle CBOR decode HTTPException with RFC 9457 Problem Details.
    """
    return CBORDecodeProblem(detail=str(exc.detail))


def unsupported_media_type_handler(
    exception_handler: ExceptionHandler,
    request: Request,
    exc: UnsupportedMediaTypeHTTPException,
) -> UnsupportedMediaTypeProblem:
    """
    Handle unsupported media type with RFC 9457 Problem Details.
    """
    return UnsupportedMediaTypeProblem(detail=str(exc.detail))


def not_acceptable_handler(
    exception_handler: ExceptionHandler,
    request: Request,
    exc: NotAcceptableHTTPException,
) -> NotAcceptableProblem:
    """
    Handle unsupported response media types with RFC 9457 Problem Details.
    """
    return NotAcceptableProblem(detail=str(exc.detail))


def invalid_cursor_error_handler(
    exception_handler: ExceptionHandler,
    request: Request,
    exc: InvalidCursorError,
) -> Problem:
    """
    Handle invalid pagination cursor with RFC 9457 Problem Details.

    Returns 400 Bad Request per HTTP semantics: an invalid cursor is a
    malformed request parameter, not a schema validation error (422).
    """
    return Problem(
        title="Bad Request",
        detail=str(exc) or "invalid cursor format",
        status=400,
    )


exception_handler = new_exception_handler(
    logger=logger,
    strict_rfc9457=True,
    documentation_uri_template="about:blank",
    request_validation_handler=cast("Handler", validation_error_handler),
    handlers={
        CBORDecodeError: cast("Handler", cbor_decode_error_handler),
        CBORDecodeHTTPException: cast("Handler", cbor_decode_http_exception_handler),
        UnsupportedMediaTypeHTTPException: cast("Handler", unsupported_media_type_handler),
        NotAcceptableHTTPException: cast("Handler", not_acceptable_handler),
        InvalidCursorError: cast("Handler", invalid_cursor_error_handler),
    },
    post_hooks=[
        cast("PostHook", schema_link_post_hook),
        cast(
            "PostHook",
            StripExtrasPostHook(
                mandatory_fields=["title", "status", "detail", "errors"],
                include=[500, 502, 503, 504],
                enabled=settings.environment == "production",
                logger=logger,
            ),
        ),
        # Must run AFTER StripExtrasPostHook since it accesses content['type']
        cast("PostHook", strip_about_blank_type_post_hook),
        cast("PostHook", CBORProblemPostHook()),
    ],
)
