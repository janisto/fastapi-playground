"""
Handled-exception middleware boundary tests.
"""

from typing import cast

import pytest
from starlette.types import Message, Receive, Scope, Send

from app.middleware.recovery import HandledExceptionMiddleware


async def _receive() -> Message:
    return {"type": "http.disconnect"}


def _scope() -> Scope:
    return cast("Scope", {"type": "http"})


async def test_failure_before_response_completion_propagates() -> None:
    async def failing_app(scope: Scope, receive: Receive, send: Send) -> None:
        del scope, receive
        await send({"type": "http.response.start", "status": 500, "headers": []})
        raise RuntimeError("failure")

    messages: list[Message] = []

    async def send(message: Message) -> None:
        messages.append(message)

    middleware = HandledExceptionMiddleware(failing_app)
    with pytest.raises(RuntimeError, match="failure"):
        await middleware(_scope(), _receive, send)

    assert messages == [{"type": "http.response.start", "status": 500, "headers": []}]


async def test_failure_after_complete_response_is_contained() -> None:
    async def handled_app(scope: Scope, receive: Receive, send: Send) -> None:
        del receive
        scope["portable.handled_exception"] = True
        await send({"type": "http.response.start", "status": 500, "headers": []})
        await send({"type": "http.response.body", "body": b"safe"})
        raise RuntimeError("sensitive failure")

    messages: list[Message] = []

    async def send(message: Message) -> None:
        messages.append(message)

    await HandledExceptionMiddleware(handled_app)(_scope(), _receive, send)

    assert messages == [
        {"type": "http.response.start", "status": 500, "headers": []},
        {"type": "http.response.body", "body": b"safe"},
    ]


async def test_unmarked_failure_after_complete_response_propagates() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del scope, receive
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"complete"})
        raise RuntimeError("background failure")

    async def send(message: Message) -> None:
        del message

    with pytest.raises(RuntimeError, match="background failure"):
        await HandledExceptionMiddleware(app)(_scope(), _receive, send)


async def test_transport_failure_propagates() -> None:
    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del receive
        scope["portable.handled_exception"] = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"body"})

    async def failing_send(message: Message) -> None:
        if message["type"] == "http.response.body":
            raise RuntimeError("transport failed")

    with pytest.raises(RuntimeError, match="transport failed"):
        await HandledExceptionMiddleware(app)(_scope(), _receive, failing_send)
