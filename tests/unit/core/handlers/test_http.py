"""
Unit tests for HTTP exception handler.
"""

import logging

import pytest
from fastapi import HTTPException
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from app.core.handlers.http import http_exception_handler
from tests.helpers.starlette_utils import build_starlette_app


def _create_app_raising(status_code: int, detail: str, headers: dict[str, str] | None = None) -> Starlette:
    """
    Build a Starlette app that raises HTTPException.
    """

    async def raise_error(request: Request) -> None:
        raise HTTPException(status_code=status_code, detail=detail, headers=headers)

    app = build_starlette_app(routes=[("/test", raise_error, ["GET"])], middleware=[])
    app.add_exception_handler(HTTPException, http_exception_handler)
    return app


class TestHTTPExceptionHandler:
    """
    Tests for http_exception_handler via app integration.
    """

    def test_returns_json_response(self) -> None:
        """
        Verify handler returns JSONResponse.
        """
        app = _create_app_raising(400, "Bad request")

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.headers.get("content-type") == "application/json"

    def test_returns_correct_status_code(self) -> None:
        """
        Verify handler returns exception's status_code.
        """
        app = _create_app_raising(404, "Not found")

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.status_code == 404

    def test_returns_detail_in_body(self) -> None:
        """
        Verify handler returns exception's detail in response body.
        """
        app = _create_app_raising(400, "Invalid input")

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.json() == {"detail": "Invalid input"}

    def test_preserves_custom_headers(self) -> None:
        """
        Verify handler preserves exception headers.
        """
        app = _create_app_raising(401, "Unauthorized", headers={"WWW-Authenticate": "Bearer"})

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer"

    @pytest.mark.parametrize(
        ("status_code", "detail"),
        [
            (400, "Bad request"),
            (401, "Unauthorized"),
            (403, "Forbidden"),
            (404, "Not found"),
            (409, "Conflict"),
            (422, "Validation error"),
        ],
    )
    def test_handles_4xx_errors(self, status_code: int, detail: str) -> None:
        """
        Verify handler correctly handles various 4xx errors.
        """
        app = _create_app_raising(status_code, detail)

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.status_code == status_code
        assert response.json() == {"detail": detail}

    @pytest.mark.parametrize(
        ("status_code", "detail"),
        [
            (500, "Internal server error"),
            (502, "Bad gateway"),
            (503, "Service unavailable"),
        ],
    )
    def test_handles_5xx_errors(self, status_code: int, detail: str) -> None:
        """
        Verify handler correctly handles various 5xx errors.
        """
        app = _create_app_raising(status_code, detail)

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.status_code == status_code
        assert response.json() == {"detail": detail}


class TestHTTPExceptionHandlerLogging:
    """
    Tests for logging behavior in http_exception_handler.
    """

    @pytest.fixture
    def mock_request(self) -> Request:
        """
        Create a minimal mock request.
        """
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test/path",
            "query_string": b"",
            "headers": [],
        }
        return Request(scope)

    async def test_logs_warning_for_4xx(self, mock_request: Request, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify 4xx errors are logged as warnings.
        """
        exc = HTTPException(status_code=404, detail="Not found")

        with caplog.at_level(logging.WARNING, logger="app.core.handlers.http"):
            await http_exception_handler(mock_request, exc)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "Client error" in caplog.records[0].message

    async def test_logs_error_for_5xx(self, mock_request: Request, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify 5xx errors are logged as errors.
        """
        exc = HTTPException(status_code=500, detail="Internal error")

        with caplog.at_level(logging.ERROR, logger="app.core.handlers.http"):
            await http_exception_handler(mock_request, exc)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert "HTTP error" in caplog.records[0].message

    async def test_log_includes_extra_data(self, mock_request: Request, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify log records include status_code, detail, and path.
        """
        exc = HTTPException(status_code=403, detail="Forbidden")

        with caplog.at_level(logging.WARNING, logger="app.core.handlers.http"):
            await http_exception_handler(mock_request, exc)

        record = caplog.records[0]
        assert record.status_code == 403
        assert record.detail == "Forbidden"
        assert record.path == "/test/path"


class TestHTTPExceptionHandlerDirect:
    """
    Direct handler function tests.
    """

    @pytest.fixture
    def mock_request(self) -> Request:
        """
        Create a minimal mock request.
        """
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
        }
        return Request(scope)

    async def test_handler_returns_json_response(self, mock_request: Request) -> None:
        """
        Verify handler function returns JSONResponse directly.
        """
        exc = HTTPException(status_code=404, detail="Not found")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 404
        assert response.body == b'{"detail":"Not found"}'

    async def test_handler_includes_headers(self, mock_request: Request) -> None:
        """
        Verify handler includes exception headers in response.
        """
        exc = HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

        response = await http_exception_handler(mock_request, exc)

        assert response.headers.get("www-authenticate") == "Bearer"
