"""
ASGI middleware to enforce maximum request body size with early abort.
"""

import json

import cbor2
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.cbor import PROBLEM_CBOR, PROBLEM_JSON, negotiate_response_media_type
from app.core.config import get_settings
from app.core.constants import PROBLEM_SCHEMA_PATH
from app.core.schema_links import build_described_by_link


class BodySizeLimitMiddleware:
    """
    Reject requests exceeding MAX_REQUEST_SIZE_BYTES with 413 without buffering entire body.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._max = get_settings().max_request_size_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}
        content_length = headers.get("content-length")
        try:
            declared_size = int(content_length) if content_length is not None else None
        except ValueError:
            declared_size = None
        if declared_size is not None and declared_size > self._max:
            await self._send_413(send, scope)
            return

        total = 0
        buffered: list[bytes] = []
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":  # pragma: no cover
                # Unexpected ASGI message type; defensive handling
                buffered.append(b"")
                more_body = False
                break
            chunk = message.get("body", b"")
            if chunk:
                total += len(chunk)
                if total > self._max:
                    await self._send_413(send, scope)
                    return
                buffered.append(chunk)
            more_body = message.get("more_body", False)

        body = b"".join(buffered)
        # Replay buffered body to downstream app via a custom receive
        sent = False

        async def replay_receive() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            # No more body
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay_receive, send)

    async def _send_413(self, send: Send, scope: Scope) -> None:
        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}

        # Build RFC 9457 Problem Details payload
        problem = {
            "title": "Payload Too Large",
            "status": 413,
            "detail": "Request body too large",
        }

        # RFC 9110-compliant content negotiation for error response
        # Check for explicit CBOR request (application/cbor or application/problem+cbor)
        # Use explicit_only=True since CBOR is non-default content type
        accept = headers.get("accept", "")
        wants_cbor = negotiate_response_media_type(accept, problem=True) == PROBLEM_CBOR

        if wants_cbor:
            payload = cbor2.dumps(problem)
            content_type = PROBLEM_CBOR
        else:
            payload = json.dumps(problem).encode("utf-8")
            content_type = PROBLEM_JSON

        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", content_type.encode("latin1")),
                    (b"content-length", str(len(payload)).encode("latin1")),
                    (b"link", build_described_by_link(PROBLEM_SCHEMA_PATH).encode("latin1")),
                    (b"vary", b"Accept"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload, "more_body": False})
