"""
Unit tests for exception handler hooks.
"""

from unittest.mock import MagicMock

from starlette.datastructures import State
from starlette.responses import JSONResponse

from app.core.cbor import CBORDecodeError
from app.core.exception_handler import (
    ERROR_SCHEMA_PATH,
    REQUEST_ID_HEADER,
    cbor_decode_error_handler,
    request_id_post_hook,
    request_id_pre_hook,
    schema_link_post_hook,
    strip_about_blank_type_post_hook,
)


class TestRequestIdPreHook:
    """
    Tests for request_id_pre_hook.
    """

    def test_sets_request_id_when_not_in_state(self) -> None:
        """
        Verify pre_hook generates request_id when not already set.
        """
        request = MagicMock()
        request.state = State()
        request.headers = {}
        exc = ValueError("test error")

        request_id_pre_hook(request, exc)

        assert hasattr(request.state, "request_id")
        request_id = request.state.request_id
        assert len(request_id) == 36
        assert request_id.count("-") == 4

    def test_uses_incoming_header_when_state_not_set(self) -> None:
        """
        Verify pre_hook uses X-Request-ID header when state not set.
        """
        request = MagicMock()
        request.state = State()
        request.headers = {REQUEST_ID_HEADER: "incoming-request-id"}
        exc = ValueError("test error")

        request_id_pre_hook(request, exc)

        assert request.state.request_id == "incoming-request-id"

    def test_preserves_existing_state_request_id(self) -> None:
        """
        Verify pre_hook does not override existing request_id in state.
        """
        request = MagicMock()
        request.state = State()
        request.state.request_id = "existing-request-id"
        request.headers = {REQUEST_ID_HEADER: "incoming-request-id"}
        exc = ValueError("test error")

        request_id_pre_hook(request, exc)

        assert request.state.request_id == "existing-request-id"


class TestRequestIdPostHook:
    """
    Tests for request_id_post_hook.
    """

    def test_adds_request_id_header_to_response(self) -> None:
        """
        Verify post_hook adds X-Request-ID header to response.
        """
        request = MagicMock()
        request.state = State()
        request.state.request_id = "test-request-id"

        content = {"type": "about:blank", "title": "Error", "status": 500}
        response = JSONResponse(content=content)

        result_content, result_response = request_id_post_hook(content, request, response)

        assert result_response.headers[REQUEST_ID_HEADER] == "test-request-id"
        assert result_content == content

    def test_handles_missing_request_id_in_state(self) -> None:
        """
        Verify post_hook handles case where request_id is not in state.
        """
        request = MagicMock()
        request.state = State()

        content = {"type": "about:blank", "title": "Error", "status": 500}
        response = JSONResponse(content=content)

        result_content, result_response = request_id_post_hook(content, request, response)

        assert REQUEST_ID_HEADER not in result_response.headers
        assert result_content == content

    def test_does_not_modify_content(self) -> None:
        """
        Verify post_hook returns content unchanged.
        """
        request = MagicMock()
        request.state = State()
        request.state.request_id = "test-request-id"

        original_content = {
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "errors": [{"location": "body.email", "message": "required"}],
        }
        response = JSONResponse(content=original_content)

        result_content, _ = request_id_post_hook(original_content, request, response)

        assert result_content == original_content


class TestStripAboutBlankTypePostHook:
    """Tests for strip_about_blank_type_post_hook."""

    def test_strips_about_blank_type(self) -> None:
        """Verify type field is removed when value is about:blank."""
        request = MagicMock()
        content = {"type": "about:blank", "title": "Error", "status": 400}
        response = JSONResponse(content=content)

        result_content, _result_response = strip_about_blank_type_post_hook(content, request, response)

        assert "type" not in result_content
        assert result_content == {"title": "Error", "status": 400}

    def test_preserves_non_about_blank_type(self) -> None:
        """Verify type field is preserved when not about:blank."""
        request = MagicMock()
        content = {"type": "https://example.com/error", "title": "Error", "status": 400}
        response = JSONResponse(content=content)

        result_content, _result_response = strip_about_blank_type_post_hook(content, request, response)

        assert result_content["type"] == "https://example.com/error"
        assert result_content == {"type": "https://example.com/error", "title": "Error", "status": 400}


class TestCborDecodeErrorHandler:
    """Tests for cbor_decode_error_handler."""

    def test_returns_cbor_decode_problem(self) -> None:
        """
        Verify handler converts CBORDecodeError to CBORDecodeProblem.
        """
        eh = MagicMock()
        request = MagicMock()
        exc = CBORDecodeError("Custom decode error")

        from app.core.cbor import CBORDecodeProblem

        result = cbor_decode_error_handler(eh, request, exc)

        assert isinstance(result, CBORDecodeProblem)
        assert result.detail == "Custom decode error"

    def test_uses_default_message(self) -> None:
        """
        Verify handler uses default detail when not specified.
        """
        eh = MagicMock()
        request = MagicMock()
        exc = CBORDecodeError()

        result = cbor_decode_error_handler(eh, request, exc)

        assert result.detail == "Invalid CBOR data"


class TestSchemaLinkPostHook:
    """Tests for schema_link_post_hook."""

    def test_adds_schema_field_to_content(self) -> None:
        """Verify $schema field is added with absolute URL."""
        request = MagicMock()
        request.base_url = "http://testserver/"
        content = {"title": "Not Found", "status": 404, "detail": "Resource not found"}
        response = JSONResponse(content=content)

        result_content, _result_response = schema_link_post_hook(content, request, response)

        assert "$schema" in result_content
        assert result_content["$schema"] == "http://testserver/schemas/ErrorModel.json"

    def test_adds_link_header_with_describedby(self) -> None:
        """Verify Link header with rel=describedBy is added."""
        request = MagicMock()
        request.base_url = "http://testserver/"
        content = {"title": "Error", "status": 500}
        response = JSONResponse(content=content)

        _result_content, result_response = schema_link_post_hook(content, request, response)

        assert "Link" in result_response.headers
        assert result_response.headers["Link"] == f'<{ERROR_SCHEMA_PATH}>; rel="describedBy"'

    def test_does_not_override_existing_schema(self) -> None:
        """Verify $schema is not overwritten if already present."""
        request = MagicMock()
        request.base_url = "http://testserver/"
        content = {"$schema": "http://custom/schema.json", "title": "Error", "status": 400}
        response = JSONResponse(content=content)

        result_content, _result_response = schema_link_post_hook(content, request, response)

        assert result_content["$schema"] == "http://custom/schema.json"

    def test_updates_content_length_header(self) -> None:
        """Verify content-length header is updated after adding $schema."""
        request = MagicMock()
        request.base_url = "http://testserver/"
        content = {"title": "Error", "status": 400}
        response = JSONResponse(content=content)
        original_length = int(response.headers["content-length"])

        _result_content, result_response = schema_link_post_hook(content, request, response)

        new_length = int(result_response.headers["content-length"])
        assert new_length > original_length

    def test_handles_base_url_with_trailing_slash(self) -> None:
        """Verify trailing slash is handled correctly."""
        request = MagicMock()
        request.base_url = "http://api.example.com/"
        content = {"title": "Conflict", "status": 409}
        response = JSONResponse(content=content)

        result_content, _result_response = schema_link_post_hook(content, request, response)

        assert result_content["$schema"] == "http://api.example.com/schemas/ErrorModel.json"
        assert "//" not in result_content["$schema"].replace("http://", "")

    def test_handles_base_url_without_trailing_slash(self) -> None:
        """Verify base_url without trailing slash works correctly."""
        request = MagicMock()
        request.base_url = "https://api.example.com"
        content = {"title": "Unauthorized", "status": 401}
        response = JSONResponse(content=content)

        result_content, _result_response = schema_link_post_hook(content, request, response)

        assert result_content["$schema"] == "https://api.example.com/schemas/ErrorModel.json"
