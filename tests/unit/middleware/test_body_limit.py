"""
Unit tests for body size limit middleware.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import cbor2
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.testclient import TestClient
from starlette.types import Receive, Scope, Send

from app.middleware.body_limit import BodySizeLimitMiddleware
from tests.helpers.starlette_utils import build_starlette_app


def _create_app(max_size: int = 1024) -> Starlette:
    """
    Create a minimal Starlette app with body limit middleware.
    """

    async def echo(request: Request) -> JSONResponse:
        body = await request.body()
        return JSONResponse({"size": len(body)})

    async def ping(request: Request) -> PlainTextResponse:
        return PlainTextResponse("pong")

    app = build_starlette_app(
        routes=[
            ("/echo", echo, ["POST"]),
            ("/ping", ping, ["GET"]),
        ],
    )

    # Patch settings before adding middleware
    with patch("app.middleware.body_limit.get_settings") as mock_settings:
        mock_settings.return_value.max_request_size_bytes = max_size
        app.add_middleware(BodySizeLimitMiddleware)  # type: ignore[arg-type]

    return app


class TestBodySizeLimit:
    """
    Tests for BodySizeLimitMiddleware.
    """

    def test_small_body_passes(self) -> None:
        """
        Verify small request body is allowed.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 1024
            app = _create_app(max_size=1024)
            with TestClient(app) as client:
                response = client.post("/echo", content=b"x" * 100)
                assert response.status_code == 200
                assert response.json()["size"] == 100

    def test_large_body_rejected_by_content_length(self) -> None:
        """
        Verify request with Content-Length exceeding limit returns 413.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100
            app = _create_app(max_size=100)
            with TestClient(app) as client:
                response = client.post("/echo", content=b"x" * 200)
                assert response.status_code == 413
                assert "too large" in response.json()["detail"].lower()

    def test_get_request_passes(self) -> None:
        """
        Verify GET requests without body are not affected.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100
            app = _create_app(max_size=100)
            with TestClient(app) as client:
                response = client.get("/ping")
                assert response.status_code == 200
                assert response.text == "pong"

    def test_exact_limit_passes(self) -> None:
        """
        Verify request body exactly at limit is allowed.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100
            app = _create_app(max_size=100)
            with TestClient(app) as client:
                response = client.post("/echo", content=b"x" * 100)
                assert response.status_code == 200

    def test_one_over_limit_rejected(self) -> None:
        """
        Verify request body one byte over limit is rejected.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100
            app = _create_app(max_size=100)
            with TestClient(app) as client:
                response = client.post("/echo", content=b"x" * 101)
                assert response.status_code == 413


class TestBodySizeLimitErrorResponse:
    """
    Tests for 413 error response RFC 9457 Problem Details format.
    """

    def test_413_response_format(self) -> None:
        """
        Verify 413 response has RFC 9457 Problem Details format.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 10
            app = _create_app(max_size=10)
            with TestClient(app) as client:
                response = client.post("/echo", content=b"x" * 100)
                assert response.status_code == 413
                assert response.headers.get("content-type") == "application/problem+json"
                body = response.json()
                assert body["title"] == "Payload Too Large"
                assert body["status"] == 413
                assert body["detail"] == "Request body too large"

    def test_413_response_detail_message(self) -> None:
        """
        Verify 413 response has meaningful detail message.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 10
            app = _create_app(max_size=10)
            with TestClient(app) as client:
                response = client.post("/echo", content=b"x" * 100)
                assert response.json()["detail"] == "Request body too large"

    def test_413_response_includes_request_id(self) -> None:
        """
        Verify 413 response includes X-Request-ID header.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 10
            app = _create_app(max_size=10)
            with TestClient(app) as client:
                response = client.post("/echo", content=b"x" * 100)
                assert response.status_code == 413
                assert "x-request-id" in response.headers

    def test_413_response_echoes_incoming_request_id(self) -> None:
        """
        Verify 413 response echoes incoming X-Request-ID header.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 10
            app = _create_app(max_size=10)
            with TestClient(app) as client:
                response = client.post(
                    "/echo",
                    content=b"x" * 100,
                    headers={"X-Request-ID": "test-request-id-123"},
                )
                assert response.status_code == 413
                assert response.headers.get("x-request-id") == "test-request-id-123"


class TestBodySizeLimitCBORNegotiation:
    """
    Tests for CBOR content negotiation in 413 responses.
    """

    def test_413_returns_cbor_when_accept_cbor(self) -> None:
        """
        Verify 413 response returns CBOR when Accept: application/cbor.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 10
            app = _create_app(max_size=10)
            with TestClient(app) as client:
                response = client.post(
                    "/echo",
                    content=b"x" * 100,
                    headers={"Accept": "application/cbor"},
                )
                assert response.status_code == 413
                assert response.headers.get("content-type") == "application/problem+cbor"
                body = cbor2.loads(response.content)
                assert body["title"] == "Payload Too Large"
                assert body["status"] == 413
                assert body["detail"] == "Request body too large"

    def test_413_returns_json_without_cbor_accept(self) -> None:
        """
        Verify 413 response returns JSON when Accept header does not include CBOR.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 10
            app = _create_app(max_size=10)
            with TestClient(app) as client:
                response = client.post(
                    "/echo",
                    content=b"x" * 100,
                    headers={"Accept": "application/json"},
                )
                assert response.status_code == 413
                assert response.headers.get("content-type") == "application/problem+json"
                body = response.json()
                assert body["title"] == "Payload Too Large"


class TestBodySizeLimitEdgeCases:
    """
    Tests for edge cases and defensive code paths.
    """

    async def test_non_http_scope_passes_through(self) -> None:
        """
        Verify non-HTTP scopes (websocket, lifespan) pass through unchanged.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100

            downstream_called = False

            async def mock_app(scope: Scope, receive: Receive, send: Send) -> None:
                nonlocal downstream_called
                downstream_called = True

            middleware = BodySizeLimitMiddleware(mock_app)
            scope: dict[str, Any] = {"type": "websocket"}
            receive = AsyncMock()
            send = AsyncMock()

            await middleware(scope, receive, send)

            assert downstream_called

    async def test_malformed_content_length_handled_gracefully(self) -> None:
        """
        Verify malformed Content-Length header doesn't crash middleware.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100

            response_started = False

            async def mock_app(scope: Scope, receive: Receive, send: Send) -> None:
                nonlocal response_started
                await receive()
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b"ok"})
                response_started = True

            middleware = BodySizeLimitMiddleware(mock_app)
            scope: dict[str, Any] = {
                "type": "http",
                "headers": [(b"content-length", b"not-a-number")],
            }

            receive_messages = [
                {"type": "http.request", "body": b"small", "more_body": False},
            ]
            receive = AsyncMock(side_effect=receive_messages)
            send = AsyncMock()

            await middleware(scope, receive, send)
            assert response_started

    async def test_request_without_content_length_uses_streaming(self) -> None:
        """
        Verify request without Content-Length is handled via streaming check.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100

            received_body = b""

            async def mock_app(scope: Scope, receive: Receive, send: Send) -> None:
                nonlocal received_body
                msg = await receive()
                received_body = msg.get("body", b"")
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b"ok"})

            middleware = BodySizeLimitMiddleware(mock_app)
            scope: dict[str, Any] = {"type": "http", "headers": []}

            receive_messages = [
                {"type": "http.request", "body": b"x" * 50, "more_body": False},
            ]
            receive = AsyncMock(side_effect=receive_messages)
            send = AsyncMock()

            await middleware(scope, receive, send)
            assert received_body == b"x" * 50

    async def test_streaming_body_exceeds_limit_returns_413(self) -> None:
        """
        Verify streaming body that exceeds limit during transfer returns 413.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100

            middleware = BodySizeLimitMiddleware(MagicMock())
            scope = {"type": "http", "headers": []}

            receive_messages = [
                {"type": "http.request", "body": b"x" * 60, "more_body": True},
                {"type": "http.request", "body": b"x" * 60, "more_body": False},
            ]
            receive = AsyncMock(side_effect=receive_messages)
            send = AsyncMock()

            await middleware(scope, receive, send)

            calls = [call[0][0] for call in send.call_args_list]
            response_start = next(c for c in calls if c.get("type") == "http.response.start")
            assert response_start["status"] == 413

    async def test_replay_receive_multiple_calls(self) -> None:
        """
        Verify replay_receive returns body on first call, empty on subsequent.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100

            receive_calls: list[Any] = []

            async def mock_app(scope: Scope, receive: Receive, send: Send) -> None:
                msg1 = await receive()
                receive_calls.append(msg1)
                msg2 = await receive()
                receive_calls.append(msg2)
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b"ok"})

            middleware = BodySizeLimitMiddleware(mock_app)
            scope: dict[str, Any] = {"type": "http", "headers": []}

            receive_messages = [
                {"type": "http.request", "body": b"test", "more_body": False},
            ]
            receive = AsyncMock(side_effect=receive_messages)
            send = AsyncMock()

            await middleware(scope, receive, send)

            assert len(receive_calls) == 2
            assert receive_calls[0]["body"] == b"test"
            assert receive_calls[0]["more_body"] is False
            assert receive_calls[1]["body"] == b""
            assert receive_calls[1]["more_body"] is False


class TestBodySizeLimitWithChunkedTransfer:
    """
    Tests for chunked transfer encoding scenarios.
    """

    async def test_multiple_chunks_within_limit(self) -> None:
        """
        Verify multiple chunks that sum within limit are accepted.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 100

            received_body = b""

            async def mock_app(scope: Scope, receive: Receive, send: Send) -> None:
                nonlocal received_body
                msg = await receive()
                received_body = msg.get("body", b"")
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b"ok"})

            middleware = BodySizeLimitMiddleware(mock_app)
            scope: dict[str, Any] = {"type": "http", "headers": []}

            receive_messages = [
                {"type": "http.request", "body": b"a" * 30, "more_body": True},
                {"type": "http.request", "body": b"b" * 30, "more_body": True},
                {"type": "http.request", "body": b"c" * 30, "more_body": False},
            ]
            receive = AsyncMock(side_effect=receive_messages)
            send = AsyncMock()

            await middleware(scope, receive, send)
            assert received_body == b"a" * 30 + b"b" * 30 + b"c" * 30

    async def test_drains_remaining_body_after_413(self) -> None:
        """
        Verify middleware drains remaining body after sending 413.
        """
        with patch("app.middleware.body_limit.get_settings") as mock_settings:
            mock_settings.return_value.max_request_size_bytes = 50

            middleware = BodySizeLimitMiddleware(MagicMock())
            scope = {"type": "http", "headers": []}

            receive_messages = [
                {"type": "http.request", "body": b"x" * 30, "more_body": True},
                {"type": "http.request", "body": b"x" * 30, "more_body": True},
                {"type": "http.request", "body": b"x" * 10, "more_body": False},
            ]
            receive = AsyncMock(side_effect=receive_messages)
            send = AsyncMock()

            await middleware(scope, receive, send)

            assert receive.call_count == 3
