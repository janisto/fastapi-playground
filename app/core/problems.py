"""
Portable RFC 9457 Problem Details errors and response rendering.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import cbor2
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.core.content_negotiation import CBOR_MEDIA_TYPE, negotiate_problem_media_type

logger = logging.getLogger(__name__)
_MAX_VALIDATION_ISSUES = 32
_MAX_DIRECT_VALIDATION_ISSUES = _MAX_VALIDATION_ISSUES - 1


@dataclass(frozen=True, slots=True)
class ErrorDefinition:
    """
    Exact public metadata for one portable error code.
    """

    status: int
    title: str
    detail: str


ERRORS: dict[str, ErrorDefinition] = {
    "invalid_request": ErrorDefinition(400, "Bad Request", "Request is malformed"),
    "unauthorized": ErrorDefinition(401, "Unauthorized", "Authentication is required or invalid"),
    "forbidden": ErrorDefinition(403, "Forbidden", "Access is forbidden"),
    "client_generated_id_unsupported": ErrorDefinition(
        403, "Forbidden", "Client-generated profile IDs are not supported"
    ),
    "relationships_unsupported": ErrorDefinition(403, "Forbidden", "Profile relationships are not supported"),
    "not_found": ErrorDefinition(404, "Not Found", "Resource not found"),
    "profile_not_found": ErrorDefinition(404, "Not Found", "Profile not found"),
    "github_not_found": ErrorDefinition(404, "Not Found", "GitHub resource not found"),
    "method_not_allowed": ErrorDefinition(405, "Method Not Allowed", "Method not allowed"),
    "not_acceptable": ErrorDefinition(406, "Not Acceptable", "No acceptable response representation is available"),
    "profile_exists": ErrorDefinition(409, "Conflict", "Profile already exists"),
    "profile_resource_mismatch": ErrorDefinition(409, "Conflict", "Profile resource does not match this endpoint"),
    "payload_too_large": ErrorDefinition(413, "Content Too Large", "Request body is too large"),
    "unsupported_media_type": ErrorDefinition(415, "Unsupported Media Type", "Request representation is not supported"),
    "validation_failed": ErrorDefinition(422, "Unprocessable Content", "Request validation failed"),
    "rate_limited": ErrorDefinition(429, "Too Many Requests", "Rate limit exceeded"),
    "github_rate_limit": ErrorDefinition(429, "Too Many Requests", "GitHub rate limit exceeded"),
    "internal_error": ErrorDefinition(500, "Internal Server Error", "Internal server error"),
    "github_upstream": ErrorDefinition(502, "Bad Gateway", "GitHub upstream response is invalid or unavailable"),
    "dependency_unavailable": ErrorDefinition(503, "Service Unavailable", "A required dependency is unavailable"),
    "github_timeout": ErrorDefinition(504, "Gateway Timeout", "GitHub request timed out"),
}


@dataclass(slots=True)
class PortableProblem(Exception):  # noqa: N818 - RFC 9457 names the public abstraction Problem
    """
    Controlled portable error with optional response fields and validation issues.
    """

    code: str
    headers: dict[str, str] = field(default_factory=dict)
    errors: list[dict[str, Any]] | None = None

    def __post_init__(self) -> None:
        if self.code not in ERRORS:
            self.code = "internal_error"
        Exception.__init__(self, self.code)

    @property
    def definition(self) -> ErrorDefinition:
        return ERRORS[self.code]


def _known_source(location: tuple[str | int, ...], *, missing: bool = False) -> dict[str, str] | None:
    if not location:
        return None
    known = {
        "name",
        "firstName",
        "lastName",
        "contactEmail",
        "phoneNumber",
        "marketingOptIn",
        "termsAccepted",
        "limit",
        "cursor",
        "category",
        "owner",
        "repo",
    }
    safe_segments: list[str] = []
    for segment in location[1:]:
        if not isinstance(segment, str) or segment not in known:
            break
        safe_segments.append(segment)
    if location[0] == "query" and safe_segments and safe_segments[-1] in known:
        return {"parameter": safe_segments[-1]}
    if location[0] == "header" and safe_segments:
        return {"header": safe_segments[-1]}
    if location[0] == "body":
        if missing:
            return {"pointer": "/"}
        return {"pointer": "/" + "/".join(safe_segments) if safe_segments else "/"}
    return None


def validation_issues(
    error: ValidationError | RequestValidationError,
    *,
    location_prefix: str | None = None,
) -> list[dict[str, Any]]:
    """
    Normalize validation failures without rejected values or attacker-owned names.
    """
    raw_errors = error.errors()
    issues: list[dict[str, Any]] = []
    for item in raw_errors[:_MAX_DIRECT_VALIDATION_ISSUES]:
        missing = str(item.get("type", "")) == "missing"
        detail = "Request field is required" if missing else "Request field is invalid"
        issue: dict[str, Any] = {"detail": detail}
        location = tuple(item.get("loc", ()))
        if location_prefix is not None:
            location = (location_prefix, *location)
        source = _known_source(location, missing=missing)
        if source is not None:
            issue["source"] = source
        issues.append(issue)
    if len(raw_errors) > _MAX_DIRECT_VALIDATION_ISSUES:
        issues.append({"detail": "Additional validation errors omitted"})
    return issues or [{"detail": "Request field is invalid"}]


def problem_document(problem: PortableProblem) -> dict[str, Any]:
    definition = problem.definition
    document: dict[str, Any] = {
        "title": definition.title,
        "status": definition.status,
        "detail": definition.detail,
        "code": problem.code,
    }
    if problem.errors:
        document["errors"] = problem.errors[:_MAX_VALIDATION_ISSUES]
    return document


def render_problem(accept: str, problem: PortableProblem) -> Response:
    """
    Encode a controlled error using best-effort GCP error negotiation.
    """
    document = problem_document(problem)
    media_type = negotiate_problem_media_type(accept)
    if media_type == CBOR_MEDIA_TYPE:
        content = cbor2.dumps(document)
    else:
        content = json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(
        content=content, status_code=problem.definition.status, headers=problem.headers, media_type=media_type
    )


async def portable_problem_handler(request: Request, exc: PortableProblem) -> Response:
    return render_problem(",".join(request.headers.getlist("accept")), exc)


async def request_validation_handler(request: Request, exc: RequestValidationError) -> Response:
    return render_problem(
        ",".join(request.headers.getlist("accept")),
        PortableProblem("validation_failed", errors=validation_issues(exc)),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    mapping = {
        401: "unauthorized",
        404: "not_found",
        405: "method_not_allowed",
        406: "not_acceptable",
        413: "payload_too_large",
        415: "unsupported_media_type",
        422: "validation_failed",
        503: "dependency_unavailable",
    }
    return render_problem(
        ",".join(request.headers.getlist("accept")),
        PortableProblem(mapping.get(exc.status_code, "internal_error"), headers=dict(exc.headers or {})),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    logger.error("Unhandled application failure", extra={"failure_type": type(exc).__name__})
    request.scope["portable.handled_exception"] = True
    return render_problem(",".join(request.headers.getlist("accept")), PortableProblem("internal_error"))
