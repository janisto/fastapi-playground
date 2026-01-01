"""
Unit tests for logging middleware and utilities.
"""

import json
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from app.middleware.logging import (
    CloudRunJSONFormatter,
    RequestContextLogMiddleware,
    get_logger,
    log_audit_event,
    setup_logging,
)
from tests.helpers.starlette_utils import build_starlette_app


class TestCloudRunJSONFormatter:
    """
    Tests for CloudRunJSONFormatter.
    """

    def test_formats_as_json(self) -> None:
        """
        Verify log output is valid JSON.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "Test message"
        assert parsed["severity"] == "INFO"
        assert "time" in parsed
        assert parsed["logger"] == "test"

    def test_severity_mapping_debug(self) -> None:
        """
        Verify DEBUG level maps correctly.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Debug message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["severity"] == "DEBUG"

    def test_severity_mapping_warning(self) -> None:
        """
        Verify WARNING level maps correctly.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["severity"] == "WARNING"

    def test_severity_mapping_error(self) -> None:
        """
        Verify ERROR level maps correctly.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["severity"] == "ERROR"

    def test_severity_mapping_critical(self) -> None:
        """
        Verify CRITICAL level maps correctly.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.CRITICAL,
            pathname="test.py",
            lineno=1,
            msg="Critical message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["severity"] == "CRITICAL"

    def test_include_source_location(self) -> None:
        """
        Verify source location is included when enabled.
        """
        formatter = CloudRunJSONFormatter(include_source=True)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        output = formatter.format(record)
        parsed = json.loads(output)
        source = parsed.get("logging.googleapis.com/sourceLocation")
        assert source is not None
        assert source["file"] == "/app/test.py"
        assert source["line"] == 42
        assert source["function"] == "test_function"

    def test_excludes_source_when_disabled(self) -> None:
        """
        Verify source location is excluded when disabled.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "logging.googleapis.com/sourceLocation" not in parsed

    def test_severity_mapping_default_for_notset(self) -> None:
        """
        Verify NOTSET level (below DEBUG) maps to DEFAULT severity.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.NOTSET,
            pathname="test.py",
            lineno=1,
            msg="Notset message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["severity"] == "DEFAULT"

    def test_includes_trace_context_when_set(self) -> None:
        """
        Verify trace and span are included when request context is set.
        """
        from app.middleware.logging import _request_context

        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        ctx = {"trace": "projects/test-proj/traces/abc123", "span_id": "def456", "trace_sampled": True}
        token = _request_context.set(ctx)
        try:
            output = formatter.format(record)
            parsed = json.loads(output)
            assert parsed["logging.googleapis.com/trace"] == "projects/test-proj/traces/abc123"
            assert parsed["logging.googleapis.com/spanId"] == "def456"
            assert parsed["logging.googleapis.com/trace_sampled"] is True
        finally:
            _request_context.reset(token)

    def test_includes_trace_sampled_false(self) -> None:
        """
        Verify trace_sampled=False is included in logs.
        """
        from app.middleware.logging import _request_context

        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        ctx = {"trace": "projects/test-proj/traces/abc123", "span_id": "def456", "trace_sampled": False}
        token = _request_context.set(ctx)
        try:
            output = formatter.format(record)
            parsed = json.loads(output)
            assert parsed["logging.googleapis.com/trace_sampled"] is False
        finally:
            _request_context.reset(token)

    def test_includes_trace_without_span(self) -> None:
        """
        Verify trace is included even when span_id is missing.
        """
        from app.middleware.logging import _request_context

        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        ctx = {"trace": "projects/test-proj/traces/abc123"}
        token = _request_context.set(ctx)
        try:
            output = formatter.format(record)
            parsed = json.loads(output)
            assert parsed["logging.googleapis.com/trace"] == "projects/test-proj/traces/abc123"
            assert "logging.googleapis.com/spanId" not in parsed
        finally:
            _request_context.reset(token)

    def test_includes_span_without_trace(self) -> None:
        """
        Verify span is included even when trace is missing.
        """
        from app.middleware.logging import _request_context

        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        ctx = {"span_id": "def456"}
        token = _request_context.set(ctx)
        try:
            output = formatter.format(record)
            parsed = json.loads(output)
            assert "logging.googleapis.com/trace" not in parsed
            assert parsed["logging.googleapis.com/spanId"] == "def456"
        finally:
            _request_context.reset(token)

    def test_skips_private_extra_fields(self) -> None:
        """
        Verify extra fields starting with underscore are excluded.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record._private_field = "should be skipped"
        record.public_field = "should be included"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "_private_field" not in parsed
        assert parsed["public_field"] == "should be included"

    def test_does_not_overwrite_official_keys(self) -> None:
        """
        Verify extra fields with official key names don't overwrite payload.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Original message",
            args=(),
            exc_info=None,
        )
        record.message = "Malicious override attempt"
        record.severity = "EMERGENCY"
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "Original message"
        assert parsed["severity"] == "INFO"

    def test_formats_exception_as_stack(self) -> None:
        """
        Verify exception info is formatted as stack trace.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "stack" in parsed
        assert "ValueError: Test error" in parsed["stack"]
        assert "Traceback" in parsed["stack"]

    def test_coerces_none_extra_to_string(self) -> None:
        """
        Verify None values in extra fields are coerced to 'null' string.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.nullable_field = None
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["nullable_field"] == "null"

    def test_formats_message_with_args(self) -> None:
        """
        Verify message formatting with %s style arguments.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User %s performed %s on %s",
            args=("user-123", "create", "profile"),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "User user-123 performed create on profile"

    def test_includes_both_time_and_timestamp_fields(self) -> None:
        """
        Verify both time and timestamp fields are present for Cloud Logging compatibility.
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "time" in parsed
        assert "timestamp" in parsed
        assert parsed["time"] == parsed["timestamp"]

    def test_handles_non_ascii_characters(self) -> None:
        """
        Verify non-ASCII characters are preserved in output (ensure_ascii=False).
        """
        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Käyttäjä päivitti profiilin 日本語",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "Käyttäjä päivitti profiilin 日本語"
        # Verify non-ASCII chars not escaped
        assert "\\u" not in output

    def test_includes_request_id_from_context(self) -> None:
        """
        Verify request_id is included from request context.
        """
        from app.middleware.logging import _request_context

        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        ctx = {"request_id": "req-abc-123"}
        token = _request_context.set(ctx)
        try:
            output = formatter.format(record)
            parsed = json.loads(output)
            assert parsed["request_id"] == "req-abc-123"
        finally:
            _request_context.reset(token)

    def test_handles_empty_request_context(self) -> None:
        """
        Verify empty context dict doesn't add trace/span/request_id fields.
        """
        from app.middleware.logging import _request_context

        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        ctx: dict[str, str | bool] = {}
        token = _request_context.set(ctx)
        try:
            output = formatter.format(record)
            parsed = json.loads(output)
            assert "logging.googleapis.com/trace" not in parsed
            assert "logging.googleapis.com/spanId" not in parsed
            assert "request_id" not in parsed
        finally:
            _request_context.reset(token)

    def test_includes_all_context_fields_together(self) -> None:
        """
        Verify trace, span_id, and request_id are all included when present.
        """
        from app.middleware.logging import _request_context

        formatter = CloudRunJSONFormatter(include_source=False)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        ctx = {
            "trace": "projects/my-proj/traces/trace-123",
            "span_id": "span-456",
            "request_id": "req-789",
        }
        token = _request_context.set(ctx)
        try:
            output = formatter.format(record)
            parsed = json.loads(output)
            assert parsed["logging.googleapis.com/trace"] == "projects/my-proj/traces/trace-123"
            assert parsed["logging.googleapis.com/spanId"] == "span-456"
            assert parsed["request_id"] == "req-789"
        finally:
            _request_context.reset(token)


class TestRequestContextLogMiddleware:
    """
    Tests for RequestContextLogMiddleware trace correlation.
    """

    def test_parses_traceparent_header(self) -> None:
        """
        Verify trace context is extracted from traceparent header.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", ping, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                response = client.get(
                    "/ping",
                    headers={"traceparent": "00-abc123def456789012345678901234-def456789012345678-01"},
                )
                assert response.status_code == 200

    def test_handles_missing_trace_header(self) -> None:
        """
        Verify middleware works without trace header.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", ping, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                response = client.get("/ping")
                assert response.status_code == 200

    def test_handles_malformed_traceparent_header(self) -> None:
        """
        Verify middleware handles malformed traceparent headers gracefully.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", ping, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                response = client.get(
                    "/ping",
                    headers={"traceparent": "malformed-header"},
                )
                assert response.status_code == 200

    def test_sets_correct_trace_context_values(self) -> None:
        """
        Verify trace and span_id are correctly parsed and stored in context.
        """
        from app.middleware.logging import _request_context

        captured_context: dict[str, str | bool] | None = None

        async def capture_context(request: Request) -> PlainTextResponse:
            nonlocal captured_context
            captured_context = _request_context.get()
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "my-project"
            app = build_starlette_app(
                routes=[("/ping", capture_context, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                response = client.get(
                    "/ping",
                    headers={"traceparent": "00-trace123abc456def7890123456789012-span456def78901234-01"},
                )
                assert response.status_code == 200

        assert captured_context is not None
        assert captured_context["trace"] == "projects/my-project/traces/trace123abc456def7890123456789012"
        assert captured_context["span_id"] == "span456def78901234"
        assert captured_context["trace_sampled"] is True
        assert "request_id" in captured_context

    def test_handles_traceparent_header_without_flags(self) -> None:
        """
        Verify traceparent with minimal flags is parsed correctly.
        """
        from app.middleware.logging import _request_context

        captured_context: dict[str, str | bool] | None = None

        async def capture_context(request: Request) -> PlainTextResponse:
            nonlocal captured_context
            captured_context = _request_context.get()
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", capture_context, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                response = client.get(
                    "/ping",
                    headers={"traceparent": "00-traceid1234567890abcdef12345678-spanid1234567890ab-00"},
                )
                assert response.status_code == 200

        assert captured_context is not None
        assert captured_context["trace"] == "projects/test-project/traces/traceid1234567890abcdef12345678"
        assert captured_context["span_id"] == "spanid1234567890ab"
        assert captured_context["trace_sampled"] is False

    def test_trace_sampled_with_invalid_flags(self) -> None:
        """
        Verify trace_sampled defaults to False when flags cannot be parsed.
        """
        from app.middleware.logging import _request_context

        captured_context: dict[str, str | bool] | None = None

        async def capture_context(request: Request) -> PlainTextResponse:
            nonlocal captured_context
            captured_context = _request_context.get()
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", capture_context, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                # Use invalid hex flags "zz"
                response = client.get(
                    "/ping",
                    headers={"traceparent": "00-traceid1234567890abcdef12345678-spanid1234567890ab-zz"},
                )
                assert response.status_code == 200

        assert captured_context is not None
        assert captured_context["trace_sampled"] is False

    def test_context_reset_after_exception(self) -> None:
        """
        Verify request context is reset even when handler raises exception.
        """
        from app.middleware.logging import _request_context

        async def raise_error(request: Request) -> PlainTextResponse:
            raise ValueError("Test error")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/error", raise_error, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app, raise_server_exceptions=False) as client:
                client.get("/error", headers={"X-Request-ID": "test-id"})

        # Context should be reset to None after request completes
        assert _request_context.get() is None


class TestRequestIdHeader:
    """
    Tests for X-Request-ID header generation and propagation.
    """

    def test_generates_request_id_when_not_provided(self) -> None:
        """
        Verify middleware generates a UUID request ID when header not present.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", ping, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                response = client.get("/ping")
                assert response.status_code == 200
                assert "X-Request-ID" in response.headers
                # Verify it's a valid UUID format
                request_id = response.headers["X-Request-ID"]
                assert len(request_id) == 36
                assert request_id.count("-") == 4

    def test_uses_incoming_request_id_header(self) -> None:
        """
        Verify middleware uses incoming X-Request-ID when provided.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", ping, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                response = client.get(
                    "/ping",
                    headers={"X-Request-ID": "custom-request-id-123"},
                )
                assert response.status_code == 200
                assert response.headers["X-Request-ID"] == "custom-request-id-123"

    def test_request_id_included_in_logs(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify request ID appears in log context.
        """
        import logging

        from app.middleware.logging import _request_context

        captured_context: dict[str, str] | None = None

        async def capture_context(request: Request) -> PlainTextResponse:
            nonlocal captured_context
            captured_context = _request_context.get()
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", capture_context, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with (
                caplog.at_level(logging.DEBUG),
                TestClient(app) as client,
            ):
                response = client.get(
                    "/ping",
                    headers={"X-Request-ID": "test-request-id"},
                )
                assert response.status_code == 200

        assert captured_context is not None
        assert captured_context.get("request_id") == "test-request-id"

    def test_request_id_stored_in_request_state(self) -> None:
        """
        Verify request_id is stored in request.state for exception handler access.
        """
        captured_request_id: str | None = None

        async def capture_state(request: Request) -> PlainTextResponse:
            nonlocal captured_request_id
            captured_request_id = getattr(request.state, "request_id", None)
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", capture_state, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                response = client.get(
                    "/ping",
                    headers={"X-Request-ID": "state-test-id"},
                )
                assert response.status_code == 200

        assert captured_request_id == "state-test-id"

    def test_request_state_request_id_generated_when_not_provided(self) -> None:
        """
        Verify request.state.request_id is generated when header not present.
        """
        captured_request_id: str | None = None

        async def capture_state(request: Request) -> PlainTextResponse:
            nonlocal captured_request_id
            captured_request_id = getattr(request.state, "request_id", None)
            return PlainTextResponse("pong")

        with patch("app.middleware.logging.get_settings") as mock_settings:
            mock_settings.return_value.firebase_project_id = "test-project"
            app = build_starlette_app(
                routes=[("/ping", capture_state, ["GET"])],
                middleware=[(RequestContextLogMiddleware, {})],
            )

            with TestClient(app) as client:
                response = client.get("/ping")
                assert response.status_code == 200

        assert captured_request_id is not None
        assert len(captured_request_id) == 36
        assert captured_request_id.count("-") == 4


class TestGetLogger:
    """
    Tests for get_logger utility.
    """

    def test_returns_logger(self) -> None:
        """
        Verify get_logger returns a Logger instance.
        """
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"


class TestLogAuditEvent:
    """
    Tests for log_audit_event utility.
    """

    def test_logs_audit_event(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify audit event is logged with correct structure.
        """
        with caplog.at_level(logging.INFO):
            log_audit_event(
                action="create",
                user_id="user-123",
                resource_type="profile",
                resource_id="profile-456",
                result="success",
            )

        assert len(caplog.records) > 0
        record = caplog.records[-1]
        assert record.message == "Audit event"
        assert hasattr(record, "audit")
        audit: dict[str, object] = record.audit  # type: ignore[attr-defined]
        assert audit["action"] == "create"

    def test_logs_audit_with_details(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify audit event includes optional details.
        """
        with caplog.at_level(logging.INFO):
            log_audit_event(
                action="delete",
                user_id="user-123",
                resource_type="profile",
                resource_id="profile-456",
                result="success",
                details={"reason": "user_request"},
            )

        assert len(caplog.records) > 0

    def test_audit_event_extra_structure(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify audit event extra dict has correct structure.
        """
        with caplog.at_level(logging.INFO):
            log_audit_event(
                action="update",
                user_id="user-abc",
                resource_type="profile",
                resource_id="profile-xyz",
                result="success",
                details={"fields": ["email", "phone"]},
            )

        assert len(caplog.records) > 0
        record = caplog.records[-1]
        assert hasattr(record, "audit")
        audit: dict[str, object] = record.audit  # type: ignore[attr-defined]
        assert audit["action"] == "update"
        assert audit["user_id"] == "user-abc"
        assert audit["resource_type"] == "profile"
        assert audit["resource_id"] == "profile-xyz"
        assert audit["result"] == "success"
        assert audit["details"] == {"fields": ["email", "phone"]}

    def test_audit_event_default_result(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify audit event uses 'success' as default result.
        """
        with caplog.at_level(logging.INFO):
            log_audit_event(
                action="create",
                user_id="user-123",
                resource_type="profile",
                resource_id="profile-456",
            )

        assert len(caplog.records) > 0
        record = caplog.records[-1]
        assert hasattr(record, "audit")
        audit: dict[str, object] = record.audit  # type: ignore[attr-defined]
        assert audit["result"] == "success"

    def test_audit_event_empty_details_default(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify audit event uses empty dict as default details.
        """
        with caplog.at_level(logging.INFO):
            log_audit_event(
                action="delete",
                user_id="user-123",
                resource_type="profile",
                resource_id="profile-456",
            )

        assert len(caplog.records) > 0
        record = caplog.records[-1]
        assert hasattr(record, "audit")
        audit: dict[str, object] = record.audit  # type: ignore[attr-defined]
        assert audit["details"] == {}

    def test_audit_event_failure_result(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify audit event can log failure result.
        """
        with caplog.at_level(logging.INFO):
            log_audit_event(
                action="create",
                user_id="user-123",
                resource_type="profile",
                resource_id="profile-456",
                result="failure",
                details={"error": "Duplicate profile"},
            )

        assert len(caplog.records) > 0
        record = caplog.records[-1]
        assert hasattr(record, "audit")
        audit: dict[str, object] = record.audit  # type: ignore[attr-defined]
        assert audit["result"] == "failure"
        details: dict[str, object] = audit["details"]  # type: ignore[assignment]
        assert details["error"] == "Duplicate profile"


class TestSetupLogging:
    """
    Tests for setup_logging function.
    """

    @pytest.fixture(autouse=True)
    def reset_logging_state(self) -> None:
        """
        Reset the global logging configuration flag before each test.
        """
        import app.middleware.logging as logging_module

        logging_module._logging_configured = False

    def test_configures_root_logger_with_json_formatter(self) -> None:
        """
        Verify setup_logging adds CloudRunJSONFormatter to root logger.
        """
        mock_settings = MagicMock()
        mock_settings.debug = False

        with patch("app.middleware.logging.get_settings", return_value=mock_settings):
            setup_logging()

        root = logging.getLogger()
        assert len(root.handlers) >= 1
        handler = root.handlers[-1]
        assert isinstance(handler.formatter, CloudRunJSONFormatter)

    def test_sets_debug_level_when_debug_enabled(self) -> None:
        """
        Verify root logger level is DEBUG when settings.debug is True.
        """
        mock_settings = MagicMock()
        mock_settings.debug = True

        with patch("app.middleware.logging.get_settings", return_value=mock_settings):
            setup_logging()

        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_sets_info_level_when_debug_disabled(self) -> None:
        """
        Verify root logger level is INFO when settings.debug is False.
        """
        mock_settings = MagicMock()
        mock_settings.debug = False

        with patch("app.middleware.logging.get_settings", return_value=mock_settings):
            setup_logging()

        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_configures_uvicorn_loggers(self) -> None:
        """
        Verify uvicorn loggers are configured to propagate.
        """
        mock_settings = MagicMock()
        mock_settings.debug = False

        with patch("app.middleware.logging.get_settings", return_value=mock_settings):
            setup_logging()

        for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
            logger = logging.getLogger(name)
            assert logger.propagate is True

    def test_uvicorn_access_stays_info_level(self) -> None:
        """
        Verify uvicorn.access stays at INFO even in debug mode.
        """
        mock_settings = MagicMock()
        mock_settings.debug = True

        with patch("app.middleware.logging.get_settings", return_value=mock_settings):
            setup_logging()

        access_logger = logging.getLogger("uvicorn.access")
        assert access_logger.level == logging.INFO

    def test_only_configures_once(self) -> None:
        """
        Verify setup_logging is idempotent.
        """
        mock_settings = MagicMock()
        mock_settings.debug = False

        with patch("app.middleware.logging.get_settings", return_value=mock_settings) as mock_get:
            setup_logging()
            setup_logging()
            setup_logging()

        assert mock_get.call_count == 1

    def test_streams_to_stdout(self) -> None:
        """
        Verify handler streams to stdout.
        """
        mock_settings = MagicMock()
        mock_settings.debug = False

        with patch("app.middleware.logging.get_settings", return_value=mock_settings):
            setup_logging()

        root = logging.getLogger()
        handler = root.handlers[-1]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stdout
