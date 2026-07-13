"""
Unit tests for exception handler hooks.
"""

from unittest.mock import MagicMock

from starlette.responses import JSONResponse

from app.core.cbor import CBORDecodeError
from app.core.constants import PROBLEM_SCHEMA_PATH, VALIDATION_PROBLEM_SCHEMA_PATH
from app.core.exception_handler import (
    cbor_decode_error_handler,
    schema_link_post_hook,
    strip_about_blank_type_post_hook,
)


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

    def test_preserves_problem_content(self) -> None:
        """Schema discovery does not mutate the Problem Details body."""
        request = MagicMock()
        content = {"title": "Not Found", "status": 404, "detail": "Resource not found"}
        response = JSONResponse(content=content)

        result_content, _result_response = schema_link_post_hook(content, request, response)

        assert result_content == content
        assert "$schema" not in result_content

    def test_adds_link_header_with_describedby(self) -> None:
        """Verify Link header with rel=describedBy is added."""
        request = MagicMock()
        content = {"title": "Error", "status": 500}
        response = JSONResponse(content=content)

        _result_content, result_response = schema_link_post_hook(content, request, response)

        assert "Link" in result_response.headers
        assert result_response.headers["Link"] == f'<{PROBLEM_SCHEMA_PATH}>; rel="describedBy"'

    def test_uses_validation_schema_for_structured_errors(self) -> None:
        """
        Verify structured validation errors use their specific schema.
        """
        request = MagicMock()
        content = {"title": "Unprocessable Entity", "status": 422, "errors": []}
        response = JSONResponse(content=content)

        _result_content, result_response = schema_link_post_hook(content, request, response)

        assert result_response.headers["Link"] == f'<{VALIDATION_PROBLEM_SCHEMA_PATH}>; rel="describedBy"'

    def test_does_not_change_content_length(self) -> None:
        """Adding a header does not rewrite the response body."""
        request = MagicMock()
        content = {"title": "Error", "status": 400}
        response = JSONResponse(content=content)
        original_length = response.headers["content-length"]

        _result_content, result_response = schema_link_post_hook(content, request, response)

        assert result_response.headers["content-length"] == original_length
