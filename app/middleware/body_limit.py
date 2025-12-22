"""
ASGI middleware to enforce maximum request body size with early abort.
"""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings


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

        # Quick check using Content-Length header when present
        try:
            headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            cl = headers.get("content-length")
            if cl is not None and int(cl) > self._max:
                await self._send_413(send)
                # Drain the incoming body to keep connection sane
                await self._drain_body(receive)
                return
        except Exception:
            # Ignore header parsing errors; rely on streaming guard
            pass

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
                    await self._send_413(send)
                    # Drain remainder if any
                    if message.get("more_body"):
                        await self._drain_body(receive)
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

    async def _send_413(self, send: Send) -> None:
        payload = json.dumps({"detail": "Request body too large"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(payload)).encode())],
            }
        )
        await send({"type": "http.response.body", "body": payload, "more_body": False})

    async def _drain_body(self, receive: Receive) -> None:
        more = True
        while more:
            message = await receive()
            if message.get("type") != "http.request":  # pragma: no cover
                break
            more = message.get("more_body", False)
