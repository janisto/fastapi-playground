"""
Route-aware ASGI request policy and streaming body limit.
"""

import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.content_negotiation import strip_http_ows
from app.core.portable_http import validate_closed_query
from app.core.problems import PortableProblem, render_problem

MAX_REQUEST_BODY_BYTES = 1_000_000
_BODY_ROUTES = {("POST", "/v1/hello"), ("POST", "/v1/profile"), ("PATCH", "/v1/profile")}
_EXACT_METHODS: dict[str, frozenset[str]] = {
    "/health": frozenset({"GET"}),
    "/v1/hello": frozenset({"GET", "POST"}),
    "/v1/items": frozenset({"GET"}),
    "/v1/profile": frozenset({"GET", "POST", "PATCH", "DELETE"}),
    "/openapi.json": frozenset({"GET"}),
}
_GITHUB_PATTERNS = (
    re.compile(r"/v1/github/owners/[^/]+\Z"),
    re.compile(r"/v1/github/owners/[^/]+/repos\Z"),
    re.compile(r"/v1/github/repos/[^/]+/[^/]+\Z"),
    re.compile(r"/v1/github/repos/[^/]+/[^/]+/(?:activity|languages|tags)\Z"),
)
_SCHEMA_PATTERN = re.compile(r"/schemas/[^/]+\Z")
_PAGINATED_GITHUB = (
    re.compile(r"/v1/github/owners/[^/]+/repos\Z"),
    re.compile(r"/v1/github/repos/[^/]+/[^/]+/(?:activity|tags)\Z"),
)
_DECIMAL_LENGTH = re.compile(r"[0-9]+\Z")
_MAX_CONTENT_LENGTH = 9_223_372_036_854_775_807


def _content_length(value: str) -> int | None:
    if _DECIMAL_LENGTH.fullmatch(value) is None:
        return None
    normalized = value.lstrip("0") or "0"
    maximum = str(_MAX_CONTENT_LENGTH)
    if len(normalized) > len(maximum) or (len(normalized) == len(maximum) and normalized > maximum):
        return None
    return int(normalized)


def _allowed_methods(path: str) -> frozenset[str] | None:
    methods = _EXACT_METHODS.get(path)
    if methods is not None:
        return methods
    if _SCHEMA_PATTERN.fullmatch(path) or any(pattern.fullmatch(path) for pattern in _GITHUB_PATTERNS):
        return frozenset({"GET"})
    return None


def _allowed_query(path: str) -> frozenset[str]:
    if path == "/v1/items":
        return frozenset({"limit", "cursor", "category"})
    if any(pattern.fullmatch(path) for pattern in _PAGINATED_GITHUB):
        return frozenset({"limit", "cursor"})
    return frozenset()


def _accept(scope: Scope) -> str:
    return ",".join(value.decode("latin1") for key, value in scope.get("headers", []) if key.lower() == b"accept")


async def _empty_receive() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}


async def _send_problem(scope: Scope, send: Send, problem: PortableProblem) -> None:
    response = render_problem(_accept(scope), problem)
    await response(scope, _empty_receive, send)


class BodySizeLimitMiddleware:
    """
    Select a portable route and method before enforcing the exact inbound limit.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._max = MAX_REQUEST_BODY_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path", ""))
        method = str(scope.get("method", ""))
        allowed_methods = _allowed_methods(path)
        if allowed_methods is not None and method not in allowed_methods:
            await _send_problem(
                scope,
                send,
                PortableProblem("method_not_allowed", headers={"Allow": ", ".join(sorted(allowed_methods))}),
            )
            return

        if allowed_methods is not None:
            try:
                scope["portable.query"] = validate_closed_query(scope.get("query_string", b""), _allowed_query(path))
            except PortableProblem as problem:
                await _send_problem(scope, send, problem)
                return

        if (method, path) not in _BODY_ROUTES:
            await self.app(scope, receive, send)
            return

        content_lengths = [
            strip_http_ows(value.decode("latin1"))
            for key, value in scope.get("headers", [])
            if key.lower() == b"content-length"
        ]
        if content_lengths:
            values = [strip_http_ows(part) for value in content_lengths for part in value.split(",")]
            parsed_lengths = [_content_length(value) for value in values]
            if not values or any(value is None for value in parsed_lengths) or len(set(parsed_lengths)) != 1:
                await _send_problem(scope, send, PortableProblem("invalid_request"))
                return
            if parsed_lengths[0] is not None and parsed_lengths[0] > self._max:
                await _send_problem(scope, send, PortableProblem("payload_too_large"))
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self._max:
                    raise PortableProblem("payload_too_large")
            return message

        await self.app(scope, limited_receive, send)
