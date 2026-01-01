"""
Unit tests for CBOR serialization support.
"""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import cbor2
import pytest
from starlette.responses import JSONResponse

from app.core.cbor import (
    ALLOWED_CONTENT_TYPES,
    CBOR_MEDIA_TYPE,
    JSON_MEDIA_TYPE,
    PROBLEM_CBOR,
    CBORDecodeError,
    CBORDecodeHTTPException,
    CBORProblemPostHook,
    CBORRequest,
    CBORResponse,
    UnsupportedMediaTypeHTTPException,
    UnsupportedMediaTypeProblem,
    accepts_media_type,
    content_type_is_allowed,
    content_type_matches,
    normalize_media_type,
)

# Type alias for the make_request fixture
MakeRequestFn = Callable[[bytes, str], CBORRequest]

# Type alias for the make_request_response fixture
MakeRequestResponseFn = Callable[[str], tuple[MagicMock, JSONResponse]]


class TestCBORDecodeError:
    """Tests for CBORDecodeError exception."""

    def test_default_message(self) -> None:
        """CBORDecodeError has default message."""
        exc = CBORDecodeError()
        assert exc.detail == "Invalid CBOR data"
        assert str(exc) == "Invalid CBOR data"

    def test_custom_message(self) -> None:
        """CBORDecodeError accepts custom message."""
        exc = CBORDecodeError("Custom error")
        assert exc.detail == "Custom error"
        assert str(exc) == "Custom error"


class TestUnsupportedMediaTypeProblem:
    """Tests for UnsupportedMediaTypeProblem."""

    def test_status_code(self) -> None:
        """UnsupportedMediaTypeProblem has 415 status."""
        exc = UnsupportedMediaTypeProblem()
        assert exc.status == 415

    def test_title(self) -> None:
        """UnsupportedMediaTypeProblem has correct title."""
        exc = UnsupportedMediaTypeProblem()
        assert exc.title == "Unsupported Media Type"


class TestCBORRequest:
    """Tests for CBORRequest body handling."""

    @pytest.fixture
    def make_request(self) -> MakeRequestFn:
        """Factory for creating CBORRequest with body and content-type."""

        def _make(body: bytes, content_type: str = "") -> CBORRequest:
            scope: dict[str, Any] = {
                "type": "http",
                "headers": [(b"content-type", content_type.encode())] if content_type else [],
            }

            async def receive() -> dict[str, Any]:
                return {"type": "http.request", "body": body}

            return CBORRequest(scope, receive)

        return _make

    async def test_json_body_unchanged(self, make_request: MakeRequestFn) -> None:
        """JSON body is returned unchanged."""
        data = {"name": "test"}
        body = json.dumps(data).encode()
        request = make_request(body, JSON_MEDIA_TYPE)

        result = await request.body()

        assert result == body

    async def test_cbor_body_decoded_to_json(self, make_request: MakeRequestFn) -> None:
        """CBOR body is decoded and re-encoded as JSON."""
        data = {"name": "test", "count": 42}
        cbor_body = cbor2.dumps(data)
        request = make_request(cbor_body, CBOR_MEDIA_TYPE)

        result = await request.body()

        decoded = json.loads(result)
        assert decoded == data

    async def test_empty_body_allowed(self, make_request: MakeRequestFn) -> None:
        """Empty body is allowed regardless of content-type."""
        request = make_request(b"", JSON_MEDIA_TYPE)

        result = await request.body()

        assert result == b""

    async def test_no_content_type_allowed(self, make_request: MakeRequestFn) -> None:
        """Missing content-type is allowed."""
        body = b"raw data"
        request = make_request(body, "")

        result = await request.body()

        assert result == body

    async def test_unsupported_content_type_raises(self, make_request: MakeRequestFn) -> None:
        """Unsupported content-type raises UnsupportedMediaTypeHTTPException."""
        request = make_request(b"data", "text/plain")

        with pytest.raises(UnsupportedMediaTypeHTTPException) as exc_info:
            await request.body()

        assert exc_info.value.status_code == 415
        assert "text/plain" in str(exc_info.value.detail)
        assert all(ct in str(exc_info.value.detail) for ct in sorted(ALLOWED_CONTENT_TYPES))

    async def test_invalid_cbor_raises(self, make_request: MakeRequestFn) -> None:
        """Invalid CBOR data raises CBORDecodeHTTPException."""
        # Use truncated CBOR: starts with map of 2 items but only has 0 bytes following
        # 0xA2 = map with 2 items, which expects content that isn't there
        request = make_request(b"\xa2", CBOR_MEDIA_TYPE)

        with pytest.raises(CBORDecodeHTTPException) as exc_info:
            await request.body()

        assert exc_info.value.status_code == 400
        assert "Failed to decode CBOR" in str(exc_info.value.detail)

    async def test_body_cached(self, make_request: MakeRequestFn) -> None:
        """Body is cached after first read."""
        data = {"key": "value"}
        cbor_body = cbor2.dumps(data)
        request = make_request(cbor_body, CBOR_MEDIA_TYPE)

        result1 = await request.body()
        result2 = await request.body()

        assert result1 == result2

    async def test_content_type_with_charset(self, make_request: MakeRequestFn) -> None:
        """Content-type with charset parameter is handled."""
        data = {"name": "test"}
        body = json.dumps(data).encode()
        request = make_request(body, "application/json; charset=utf-8")

        result = await request.body()

        assert result == body


class TestCBORResponse:
    """Tests for CBORResponse serialization."""

    def test_media_type(self) -> None:
        """CBORResponse has correct media type."""
        assert CBORResponse.media_type == CBOR_MEDIA_TYPE

    def test_dict_serialization(self) -> None:
        """Dictionary is serialized to CBOR."""
        data = {"name": "test", "value": 123}
        response = CBORResponse(content=data)

        decoded = cbor2.loads(response.body)
        assert decoded == data

    def test_list_serialization(self) -> None:
        """List is serialized to CBOR."""
        data = [1, 2, 3]
        response = CBORResponse(content=data)

        decoded = cbor2.loads(response.body)
        assert decoded == data

    def test_datetime_as_timestamp(self) -> None:
        """Datetime is serialized with CBOR tag 1 (epoch timestamp) and decoded back to datetime."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        data = {"created_at": dt}
        response = CBORResponse(content=data)

        # cbor2 uses tag 1 for epoch timestamp, which when decoded returns a datetime
        decoded = cbor2.loads(response.body)
        assert decoded["created_at"] == dt

    def test_nested_structure(self) -> None:
        """Nested structures are serialized correctly."""
        data = {
            "user": {"name": "test", "active": True},
            "items": [{"id": 1}, {"id": 2}],
        }
        response = CBORResponse(content=data)

        decoded = cbor2.loads(response.body)
        assert decoded == data


class TestCBORProblemPostHook:
    """Tests for CBORProblemPostHook."""

    @pytest.fixture
    def hook(self) -> CBORProblemPostHook:
        """Create hook instance."""
        return CBORProblemPostHook()

    @pytest.fixture
    def make_request_response(self) -> MakeRequestResponseFn:
        """Factory for creating mock request and response."""

        def _make(accept: str = "") -> tuple[MagicMock, JSONResponse]:
            request = MagicMock()
            request.headers = {"accept": accept} if accept else {}
            content = {"type": "about:blank", "title": "Error", "status": 400}
            response = JSONResponse(content=content, status_code=400)
            return request, response

        return _make

    def test_json_accept_unchanged(
        self,
        hook: CBORProblemPostHook,
        make_request_response: MakeRequestResponseFn,
    ) -> None:
        """JSON Accept header leaves response unchanged."""
        request, response = make_request_response("application/json")
        content = {"type": "about:blank", "title": "Error", "status": 400}
        original_body = response.body

        result_content, result_response = hook(content, request, response)

        assert result_response.body == original_body
        assert result_content == content

    def test_cbor_accept_serializes_body(
        self,
        hook: CBORProblemPostHook,
        make_request_response: MakeRequestResponseFn,
    ) -> None:
        """CBOR Accept header serializes body as CBOR."""
        request, response = make_request_response(CBOR_MEDIA_TYPE)
        content = {"type": "about:blank", "title": "Error", "status": 400}

        result_content, result_response = hook(content, request, response)

        decoded = cbor2.loads(result_response.body)
        assert decoded == content
        assert result_response.headers["content-type"] == PROBLEM_CBOR
        assert result_content == content

    def test_cbor_accept_updates_content_length(
        self,
        hook: CBORProblemPostHook,
        make_request_response: MakeRequestResponseFn,
    ) -> None:
        """CBOR Accept updates content-length header."""
        request, response = make_request_response(CBOR_MEDIA_TYPE)
        content = {"type": "about:blank", "title": "Error", "status": 400}

        result_content, result_response = hook(content, request, response)

        expected_length = len(cbor2.dumps(content))
        assert result_response.headers["content-length"] == str(expected_length)
        assert result_content == content

    def test_no_accept_header_unchanged(
        self,
        hook: CBORProblemPostHook,
        make_request_response: MakeRequestResponseFn,
    ) -> None:
        """Missing Accept header leaves response unchanged."""
        request, response = make_request_response("")
        content = {"type": "about:blank", "title": "Error", "status": 400}
        original_content_type = response.headers.get("content-type")

        result_content, result_response = hook(content, request, response)

        assert result_response.headers.get("content-type") == original_content_type
        assert result_content == content

    def test_mixed_accept_with_cbor(
        self,
        hook: CBORProblemPostHook,
        make_request_response: MakeRequestResponseFn,
    ) -> None:
        """Accept header containing CBOR triggers CBOR serialization."""
        request, response = make_request_response("application/json, application/cbor")
        content = {"type": "about:blank", "title": "Error", "status": 400}

        result_content, result_response = hook(content, request, response)

        decoded = cbor2.loads(result_response.body)
        assert decoded == content
        assert result_content == content

    def test_problem_cbor_accept_serializes_body(
        self,
        hook: CBORProblemPostHook,
        make_request_response: MakeRequestResponseFn,
    ) -> None:
        """application/problem+cbor Accept header serializes body as CBOR."""
        request, response = make_request_response(PROBLEM_CBOR)
        content = {"type": "about:blank", "title": "Error", "status": 400}

        result_content, result_response = hook(content, request, response)

        decoded = cbor2.loads(result_response.body)
        assert decoded == content
        assert result_response.headers["content-type"] == PROBLEM_CBOR
        assert result_content == content


class TestCBORConstants:
    """Tests for CBOR constants."""

    def test_media_types(self) -> None:
        """Media type constants are correct."""
        assert CBOR_MEDIA_TYPE == "application/cbor"
        assert JSON_MEDIA_TYPE == "application/json"
        assert PROBLEM_CBOR == "application/problem+cbor"

    def test_allowed_content_types(self) -> None:
        """Allowed content types include JSON and CBOR."""
        assert JSON_MEDIA_TYPE in ALLOWED_CONTENT_TYPES
        assert CBOR_MEDIA_TYPE in ALLOWED_CONTENT_TYPES
        assert len(ALLOWED_CONTENT_TYPES) == 2


class TestCBORRequestUpdateContentType:
    """Tests for CBORRequest._update_content_type_to_json."""

    def test_update_content_type_clears_cached_headers(self) -> None:
        """
        Verify _update_content_type_to_json clears cached _headers if present.
        """
        scope: dict[str, Any] = {
            "type": "http",
            "headers": [(b"content-type", b"application/cbor")],
        }

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": b""}

        request = CBORRequest(scope, receive)
        # Access headers to populate the cache
        _ = request.headers
        assert hasattr(request, "_headers")

        # Now call the method
        request._update_content_type_to_json()

        # The _headers cache should be cleared
        assert not hasattr(request, "_headers")
        # New headers should contain application/json
        new_content_type = None
        for key, value in scope["headers"]:
            if key.lower() == b"content-type":
                new_content_type = value
                break
        assert new_content_type == b"application/json"

    def test_update_content_type_without_cached_headers(self) -> None:
        """
        Verify _update_content_type_to_json works when _headers not cached.
        """
        scope: dict[str, Any] = {
            "type": "http",
            "headers": [(b"content-type", b"application/cbor")],
        }

        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": b""}

        request = CBORRequest(scope, receive)
        # Don't access headers, so _headers is not populated
        assert not hasattr(request, "_headers")

        # Now call the method
        request._update_content_type_to_json()

        # Headers in scope should be updated
        new_content_type = None
        for key, value in scope["headers"]:
            if key.lower() == b"content-type":
                new_content_type = value
                break
        assert new_content_type == b"application/json"


class TestCBORRoute:
    """Tests for CBORRoute handler."""

    def test_no_accept_header_returns_json(self) -> None:
        """
        Verify response remains JSON when Accept header is empty.

        This tests the path where Accept header is present but empty.
        """
        from fastapi import APIRouter, FastAPI
        from fastapi.testclient import TestClient

        from app.core.cbor import CBORRoute

        router = APIRouter(route_class=CBORRoute)

        @router.get("/test")
        async def get_test() -> dict[str, str]:
            return {"message": "hello"}

        app = FastAPI()
        app.include_router(router)

        # Create test client and manually construct request without Accept header
        with TestClient(app, headers={}) as client:
            # Override default headers by setting empty accept
            response = client.get("/test", headers={"Accept": ""})

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert response.json() == {"message": "hello"}

    def test_non_cbor_accept_returns_json_unchanged(self) -> None:
        """
        Verify JSON response when Accept header doesn't include CBOR.

        Tests the branch where CBOR_MEDIA_TYPE is not in accept header.
        """
        from fastapi import APIRouter, FastAPI
        from fastapi.testclient import TestClient

        from app.core.cbor import CBORRoute

        router = APIRouter(route_class=CBORRoute)

        @router.get("/test")
        async def get_test() -> dict[str, str]:
            return {"message": "hello"}

        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            # Explicitly request only JSON (no CBOR)
            response = client.get("/test", headers={"Accept": "application/json"})

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert response.json() == {"message": "hello"}

    def test_no_accept_header_in_scope_returns_json(self) -> None:
        """
        Verify response remains JSON when no Accept header exists in scope.

        Tests the branch where the for loop exits without finding b"accept" key.
        """
        import httpx
        from fastapi import APIRouter, FastAPI
        from fastapi.testclient import TestClient

        from app.core.cbor import CBORRoute

        router = APIRouter(route_class=CBORRoute)

        @router.get("/test")
        async def get_test() -> dict[str, str]:
            return {"message": "hello"}

        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            # Send request with explicit headers that don't include Accept
            req = httpx.Request(
                "GET",
                "http://testserver/test",
                headers=[("Host", "testserver"), ("User-Agent", "test")],
            )
            response = client._transport.handle_request(req)

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]


class TestNormalizeMediaType:
    """Tests for normalize_media_type function (RFC 9110 Section 8.3.1)."""

    def test_lowercases_media_type(self) -> None:
        """Media types are case-insensitive, should be normalized to lowercase."""
        assert normalize_media_type("APPLICATION/JSON") == "application/json"
        assert normalize_media_type("Application/Cbor") == "application/cbor"

    def test_strips_parameters(self) -> None:
        """Parameters like charset should be stripped."""
        assert normalize_media_type("application/json; charset=utf-8") == "application/json"
        assert normalize_media_type("text/html; charset=ISO-8859-1") == "text/html"

    def test_strips_whitespace(self) -> None:
        """Whitespace should be stripped."""
        assert normalize_media_type("  application/json  ") == "application/json"
        assert normalize_media_type(" application/json ; charset=utf-8 ") == "application/json"

    def test_handles_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert normalize_media_type("") == ""

    def test_preserves_valid_media_type(self) -> None:
        """Valid lowercase media type is preserved."""
        assert normalize_media_type("application/json") == "application/json"
        assert normalize_media_type("application/cbor") == "application/cbor"


class TestAcceptsMediaType:
    """Tests for accepts_media_type function (RFC 9110 Section 12.5.1)."""

    def test_exact_match_case_insensitive(self) -> None:
        """Exact match should be case-insensitive."""
        assert accepts_media_type("application/cbor", "application/cbor") is True
        assert accepts_media_type("APPLICATION/CBOR", "application/cbor") is True
        assert accepts_media_type("Application/Cbor", "APPLICATION/CBOR") is True

    def test_returns_false_for_empty_header(self) -> None:
        """Empty Accept header returns False."""
        assert accepts_media_type("", "application/cbor") is False

    def test_returns_false_when_not_in_list(self) -> None:
        """Returns False when media type not in Accept header."""
        assert accepts_media_type("application/json", "application/cbor") is False
        assert accepts_media_type("text/html, text/plain", "application/cbor") is False

    def test_multiple_media_types(self) -> None:
        """Handles multiple media types in Accept header."""
        assert accepts_media_type("application/json, application/cbor", "application/cbor") is True
        assert accepts_media_type("text/html, application/json, application/cbor", "application/cbor") is True

    def test_qvalue_zero_means_not_acceptable(self) -> None:
        """q=0 means the media type is explicitly not acceptable."""
        assert accepts_media_type("application/cbor;q=0", "application/cbor") is False
        assert accepts_media_type("application/cbor; q=0", "application/cbor") is False
        assert accepts_media_type("application/cbor;Q=0", "application/cbor") is False

    def test_qvalue_greater_than_zero_is_acceptable(self) -> None:
        """q>0 means the media type is acceptable."""
        assert accepts_media_type("application/cbor;q=0.1", "application/cbor") is True
        assert accepts_media_type("application/cbor;q=1", "application/cbor") is True
        assert accepts_media_type("application/cbor;q=0.5", "application/cbor") is True

    def test_wildcard_matches_all(self) -> None:
        """*/* wildcard matches any media type."""
        assert accepts_media_type("*/*", "application/cbor") is True
        assert accepts_media_type("*/*", "application/json") is True

    def test_type_wildcard_matches_subtype(self) -> None:
        """application/* matches application/cbor."""
        assert accepts_media_type("application/*", "application/cbor") is True
        assert accepts_media_type("application/*", "application/json") is True
        assert accepts_media_type("text/*", "application/cbor") is False

    def test_explicit_only_skips_wildcards(self) -> None:
        """explicit_only=True skips wildcard matching."""
        assert accepts_media_type("*/*", "application/cbor", explicit_only=True) is False
        assert accepts_media_type("application/*", "application/cbor", explicit_only=True) is False
        # But exact match still works
        assert accepts_media_type("application/cbor", "application/cbor", explicit_only=True) is True

    def test_invalid_qvalue_defaults_to_one(self) -> None:
        """Invalid q value defaults to 1.0 (acceptable)."""
        assert accepts_media_type("application/cbor;q=invalid", "application/cbor") is True
        assert accepts_media_type("application/cbor;q=", "application/cbor") is True

    def test_handles_whitespace_in_accept_header(self) -> None:
        """Handles extra whitespace in Accept header."""
        assert accepts_media_type("  application/cbor  ", "application/cbor") is True
        assert accepts_media_type("application/json , application/cbor", "application/cbor") is True

    def test_skips_empty_segments_in_accept_header(self) -> None:
        """Skips empty segments between commas in Accept header."""
        assert accepts_media_type("application/json,,application/cbor", "application/cbor") is True
        assert accepts_media_type(",application/cbor", "application/cbor") is True
        assert accepts_media_type("application/cbor,", "application/cbor") is True
        assert accepts_media_type(", , application/cbor", "application/cbor") is True

    def test_handles_malformed_media_range(self) -> None:
        """Skips malformed media ranges without slash."""
        assert accepts_media_type("invalid, application/cbor", "application/cbor") is True
        assert accepts_media_type("invalid", "application/cbor") is False

    def test_media_type_with_parameters(self) -> None:
        """Accept header with media type parameters."""
        assert accepts_media_type("application/json; charset=utf-8", "application/json") is True


class TestContentTypeMatches:
    """Tests for content_type_matches function."""

    def test_exact_match(self) -> None:
        """Exact match returns True."""
        assert content_type_matches("application/json", "application/json") is True
        assert content_type_matches("application/cbor", "application/cbor") is True

    def test_case_insensitive(self) -> None:
        """Matching is case-insensitive."""
        assert content_type_matches("APPLICATION/JSON", "application/json") is True
        assert content_type_matches("application/json", "APPLICATION/JSON") is True

    def test_ignores_parameters(self) -> None:
        """Parameters are ignored for matching."""
        assert content_type_matches("application/json; charset=utf-8", "application/json") is True
        assert content_type_matches("application/json", "application/json; charset=utf-8") is True

    def test_no_match_returns_false(self) -> None:
        """Non-matching types return False."""
        assert content_type_matches("application/json", "application/cbor") is False
        assert content_type_matches("text/html", "application/json") is False


class TestContentTypeIsAllowed:
    """Tests for content_type_is_allowed function."""

    def test_matches_allowed_types(self) -> None:
        """Returns True when content type is in allowed set."""
        assert content_type_is_allowed("application/json", ALLOWED_CONTENT_TYPES) is True
        assert content_type_is_allowed("application/cbor", ALLOWED_CONTENT_TYPES) is True

    def test_case_insensitive(self) -> None:
        """Matching is case-insensitive."""
        assert content_type_is_allowed("APPLICATION/JSON", ALLOWED_CONTENT_TYPES) is True
        assert content_type_is_allowed("Application/Cbor", ALLOWED_CONTENT_TYPES) is True

    def test_ignores_parameters(self) -> None:
        """Parameters are ignored."""
        assert content_type_is_allowed("application/json; charset=utf-8", ALLOWED_CONTENT_TYPES) is True

    def test_returns_false_for_unknown(self) -> None:
        """Returns False for unknown content types."""
        assert content_type_is_allowed("text/plain", ALLOWED_CONTENT_TYPES) is False
        assert content_type_is_allowed("application/xml", ALLOWED_CONTENT_TYPES) is False
