"""
Unit tests for domain exception handler.
"""

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.testclient import TestClient

from app.core.handlers.domain import domain_exception_handler
from app.exceptions import DomainError
from app.exceptions.profile import ProfileAlreadyExistsError, ProfileNotFoundError
from tests.helpers.starlette_utils import build_starlette_app


class _CustomDomainError(DomainError):
    """
    Custom domain error for testing.
    """

    status_code = 418
    detail = "I'm a teapot"


def _create_app_raising(error: DomainError) -> Starlette:
    """
    Build a Starlette app that raises the given domain error.
    """

    async def raise_error(request: Request) -> None:
        raise error

    app = build_starlette_app(routes=[("/test", raise_error, ["GET"])], middleware=[])
    app.add_exception_handler(DomainError, domain_exception_handler)
    return app


class TestDomainExceptionHandler:
    """
    Tests for domain_exception_handler.
    """

    async def test_returns_json_response(self) -> None:
        """
        Verify handler returns JSONResponse.
        """
        error = ProfileNotFoundError()
        app = _create_app_raising(error)

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.headers.get("content-type") == "application/json"

    async def test_returns_correct_status_code(self) -> None:
        """
        Verify handler returns exception's status_code.
        """
        error = ProfileNotFoundError()
        app = _create_app_raising(error)

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.status_code == 404

    async def test_returns_detail_in_body(self) -> None:
        """
        Verify handler returns exception's detail in response body.
        """
        error = ProfileNotFoundError()
        app = _create_app_raising(error)

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.json() == {"detail": "Profile not found"}

    async def test_handles_conflict_error(self) -> None:
        """
        Verify handler returns 409 for conflict errors.
        """
        error = ProfileAlreadyExistsError()
        app = _create_app_raising(error)

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.status_code == 409
        assert response.json() == {"detail": "Profile already exists"}

    async def test_handles_custom_domain_error(self) -> None:
        """
        Verify handler works with custom DomainError subclasses.
        """
        error = _CustomDomainError()
        app = _create_app_raising(error)

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.status_code == 418
        assert response.json() == {"detail": "I'm a teapot"}

    async def test_handles_custom_detail_message(self) -> None:
        """
        Verify handler uses custom detail if provided.
        """
        error = ProfileNotFoundError(detail="User profile with ID xyz not found")
        app = _create_app_raising(error)

        with TestClient(app) as client:
            response = client.get("/test")

        assert response.status_code == 404
        assert response.json() == {"detail": "User profile with ID xyz not found"}


class TestDomainExceptionHandlerDirect:
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
        error = ProfileNotFoundError()

        response = await domain_exception_handler(mock_request, error)

        assert response.status_code == 404
        assert response.body == b'{"detail":"Profile not found"}'

    async def test_handler_uses_exception_status_code(self, mock_request: Request) -> None:
        """
        Verify handler uses status_code from exception.
        """
        error = ProfileAlreadyExistsError()

        response = await domain_exception_handler(mock_request, error)

        assert response.status_code == 409

    async def test_handler_includes_custom_headers(self, mock_request: Request) -> None:
        """
        Verify handler includes custom headers from exception.
        """
        error = DomainError(headers={"X-Custom-Header": "test-value", "Retry-After": "60"})

        response = await domain_exception_handler(mock_request, error)

        assert response.headers.get("X-Custom-Header") == "test-value"
        assert response.headers.get("Retry-After") == "60"

    async def test_handler_handles_none_headers(self, mock_request: Request) -> None:
        """
        Verify handler works when headers is None.
        """
        error = ProfileNotFoundError()

        response = await domain_exception_handler(mock_request, error)

        assert response.status_code == 404
        assert "X-Custom-Header" not in response.headers
