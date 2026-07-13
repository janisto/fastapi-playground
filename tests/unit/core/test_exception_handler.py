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

    def test_adds_schema_field_to_content(self) -> None:
        """Verify $schema field is added with absolute URL."""
        request = MagicMock()
        request.base_url = "http://testserver/"
        content = {"title": "Not Found", "status": 404, "detail": "Resource not found"}
        response = JSONResponse(content=content)

        result_content, _result_response = schema_link_post_hook(content, request, response)

        assert "$schema" in result_content
        assert result_content["$schema"] == "http://testserver/schemas/ProblemResponse.json"

    def test_adds_link_header_with_describedby(self) -> None:
        """Verify Link header with rel=describedBy is added."""
        request = MagicMock()
        request.base_url = "http://testserver/"
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
        request.base_url = "http://testserver/"
        content = {"title": "Unprocessable Entity", "status": 422, "errors": []}
        response = JSONResponse(content=content)

        result_content, result_response = schema_link_post_hook(content, request, response)

        assert result_content["$schema"] == f"http://testserver{VALIDATION_PROBLEM_SCHEMA_PATH}"
        assert result_response.headers["Link"] == f'<{VALIDATION_PROBLEM_SCHEMA_PATH}>; rel="describedBy"'

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

        assert result_content["$schema"] == "http://api.example.com/schemas/ProblemResponse.json"
        assert "//" not in result_content["$schema"].replace("http://", "")

    def test_handles_base_url_without_trailing_slash(self) -> None:
        """Verify base_url without trailing slash works correctly."""
        request = MagicMock()
        request.base_url = "https://api.example.com"
        content = {"title": "Unauthorized", "status": 401}
        response = JSONResponse(content=content)

        result_content, _result_response = schema_link_post_hook(content, request, response)

        assert result_content["$schema"] == "https://api.example.com/schemas/ProblemResponse.json"
