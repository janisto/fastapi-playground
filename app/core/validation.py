"""
Custom validation error handler for structured error format.
"""

from collections.abc import Sequence
from typing import Any

from fastapi.exceptions import RequestValidationError
from fastapi_problem.handler import ExceptionHandler
from rfc9457 import Problem
from starlette.requests import Request

from app.core.constants import ERROR_SCHEMA_PATH

SENSITIVE_FIELD_NAMES = frozenset(
    {
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "credential",
        "credentials",
        "private_key",
    }
)


def loc_to_dot_notation(loc: Sequence[str | int]) -> str:
    """
    Convert Pydantic loc tuple to dot notation string.

    Examples:
        ('body', 'email') -> 'body.email'
        ('body', 'items', 0, 'name') -> 'body.items[0].name'
    """
    parts: list[str] = []
    for segment in loc:
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        elif parts:
            parts.append(f".{segment}")
        else:
            parts.append(segment)
    return "".join(parts)


def is_sensitive_field(loc: Sequence[str | int]) -> bool:
    """Check if any segment of the location path is a sensitive field."""
    return any(isinstance(segment, str) and segment.lower() in SENSITIVE_FIELD_NAMES for segment in loc)


def validation_error_handler(
    eh: ExceptionHandler,
    request: Request,
    exc: RequestValidationError,
) -> Problem:
    """
    Custom validation handler producing structured error format.

    Per RFC 9457, when type is omitted it defaults to "about:blank", and title
    SHOULD match the HTTP status phrase. The response includes $schema for
    JSON Schema discoverability.

    Response format:
    {
        "$schema": "http://example.com/schemas/ErrorModel.json",
        "title": "Unprocessable Entity",
        "status": 422,
        "detail": "validation failed",
        "errors": [{"location": "body.email", "message": "...", "value": "..."}]
    }
    """
    errors: list[dict[str, Any]] = []
    for error in exc.errors():
        loc = error["loc"]
        error_detail: dict[str, Any] = {
            "location": loc_to_dot_notation(loc),
            "message": error["msg"],
        }
        if "input" in error and not is_sensitive_field(loc):
            error_detail["value"] = error["input"]
        errors.append(error_detail)

    # Build absolute $schema URL from request base URL
    schema_url = str(request.base_url).rstrip("/") + ERROR_SCHEMA_PATH

    # Note: $schema is passed via **kwargs to Problem.extras, not as a named parameter
    extras: dict[str, Any] = {"$schema": schema_url, "errors": errors}
    return Problem(
        title="Unprocessable Entity",
        detail="validation failed",
        status=422,
        **extras,
    )
