"""
Custom validation error handler for structured error format.
"""

import math
from collections.abc import Sequence
from typing import Any

from fastapi.exceptions import RequestValidationError
from fastapi_problem.handler import ExceptionHandler
from rfc9457 import Problem
from starlette.requests import Request

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
_SENSITIVE_FIELD_MARKERS = tuple(name.replace("_", "") for name in SENSITIVE_FIELD_NAMES)
_MIN_SENSITIVE_COMPOSITE_MARKER_LENGTH = 5
_SENSITIVE_COMPOSITE_MARKERS = tuple(
    marker for marker in _SENSITIVE_FIELD_MARKERS if len(marker) >= _MIN_SENSITIVE_COMPOSITE_MARKER_LENGTH
)
_MAX_EXPOSED_VALUE_LENGTH = 200
_MAX_VALIDATION_ERRORS = 100
_MAX_VALIDATION_TEXT_LENGTH = 200


def _safe_validation_text(value: str) -> str:
    """
    Return bounded UTF-8 text suitable for a JSON or CBOR error response.
    """
    return value.encode("utf-8", errors="replace").decode("utf-8")[:_MAX_VALIDATION_TEXT_LENGTH]


def _is_safe_validation_string(value: str) -> bool:
    if len(value) > _MAX_EXPOSED_VALUE_LENGTH:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


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
    """
    Check if any segment of the location path is a sensitive field.
    """
    for segment in loc:
        if not isinstance(segment, str):
            continue
        normalized = "".join(character for character in segment.lower() if character.isalnum())
        if normalized in _SENSITIVE_FIELD_MARKERS or any(
            marker in normalized for marker in _SENSITIVE_COMPOSITE_MARKERS
        ):
            return True
    return False


def is_safe_validation_value(value: object) -> bool:
    """
    Return whether a validation value is safe to echo to the caller.

    Container values are omitted because Pydantic can attach the complete
    request body to a missing-field error.
    """
    if isinstance(value, str):
        return _is_safe_validation_string(value)
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, int):
        return len(str(value)) <= _MAX_EXPOSED_VALUE_LENGTH
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def validation_error_handler(
    exception_handler: ExceptionHandler,
    request: Request,
    exc: RequestValidationError,
) -> Problem:
    """
    Custom validation handler producing structured error format.

    Per RFC 9457, when type is omitted it defaults to "about:blank", and title
    SHOULD match the HTTP status phrase. A response Link header provides
    schema discoverability.

    Response format:
    {
        "title": "Unprocessable Entity",
        "status": 422,
        "detail": "validation failed",
        "errors": [{"location": "body.email", "message": "...", "value": "..."}]
    }
    """
    validation_errors = exc.errors()
    errors: list[dict[str, Any]] = []
    for error in validation_errors[:_MAX_VALIDATION_ERRORS]:
        loc = error["loc"]
        error_detail: dict[str, Any] = {
            "location": _safe_validation_text(loc_to_dot_notation(loc)),
            "message": _safe_validation_text(error["msg"]),
        }
        if "input" in error and not is_sensitive_field(loc) and is_safe_validation_value(error["input"]):
            error_detail["value"] = error["input"]
        errors.append(error_detail)
    extensions: dict[str, Any] = {"errors": errors}
    if len(validation_errors) > _MAX_VALIDATION_ERRORS:
        extensions["errors_truncated"] = True
    return Problem(
        title="Unprocessable Entity",
        detail="validation failed",
        status=422,
        **extensions,
    )
