"""
Unit tests for validation exception handler.
"""

import logging

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.testclient import TestClient

from app.core.handlers.validation import validation_exception_handler


class _TestModel(BaseModel):
    """
    Test model for validation.
    """

    name: str = Field(..., min_length=1)
    age: int = Field(..., ge=0)


def _create_app() -> FastAPI:
    """
    Build a FastAPI app with validation.
    """
    app = FastAPI()

    @app.post("/test")
    async def create_item(item: _TestModel) -> dict[str, str | int]:
        return {"name": item.name, "age": item.age}

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    return app


class TestValidationExceptionHandler:
    """
    Tests for validation_exception_handler via app integration.
    """

    def test_returns_422_status_code(self) -> None:
        """
        Verify handler returns 422 for validation errors.
        """
        app = _create_app()

        with TestClient(app) as client:
            response = client.post("/test", json={})

        assert response.status_code == 422

    def test_returns_json_response(self) -> None:
        """
        Verify handler returns JSONResponse.
        """
        app = _create_app()

        with TestClient(app) as client:
            response = client.post("/test", json={})

        assert response.headers.get("content-type") == "application/json"

    def test_returns_detail_with_errors(self) -> None:
        """
        Verify handler returns validation errors in detail.
        """
        app = _create_app()

        with TestClient(app) as client:
            response = client.post("/test", json={})

        body = response.json()
        assert "detail" in body
        assert isinstance(body["detail"], list)
        assert len(body["detail"]) >= 1

    def test_missing_required_field(self) -> None:
        """
        Verify handler reports missing required fields.
        """
        app = _create_app()

        with TestClient(app) as client:
            response = client.post("/test", json={"name": "John"})

        body = response.json()
        errors = body["detail"]

        age_error = next((e for e in errors if "age" in str(e.get("loc", []))), None)
        assert age_error is not None
        assert age_error["type"] == "missing"

    def test_invalid_type(self) -> None:
        """
        Verify handler reports type errors.
        """
        app = _create_app()

        with TestClient(app) as client:
            response = client.post("/test", json={"name": "John", "age": "not-a-number"})

        body = response.json()
        errors = body["detail"]

        age_error = next((e for e in errors if "age" in str(e.get("loc", []))), None)
        assert age_error is not None
        assert "int" in age_error["type"]

    def test_constraint_violation(self) -> None:
        """
        Verify handler reports constraint violations.
        """
        app = _create_app()

        with TestClient(app) as client:
            response = client.post("/test", json={"name": "", "age": 25})

        body = response.json()
        errors = body["detail"]

        name_error = next((e for e in errors if "name" in str(e.get("loc", []))), None)
        assert name_error is not None

    def test_multiple_errors(self) -> None:
        """
        Verify handler returns all validation errors at once.
        """
        app = _create_app()

        with TestClient(app) as client:
            response = client.post("/test", json={"name": "", "age": -5})

        body = response.json()
        errors = body["detail"]

        assert len(errors) >= 2


class TestValidationExceptionHandlerLogging:
    """
    Tests for logging behavior in validation_exception_handler.
    """

    @pytest.fixture
    def mock_request(self) -> Request:
        """
        Create a minimal mock request.
        """
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/test/path",
            "query_string": b"",
            "headers": [],
        }
        return Request(scope)

    async def test_logs_warning(self, mock_request: Request, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify validation errors are logged as warnings.
        """
        errors = [{"loc": ("body", "name"), "msg": "Field required", "type": "missing"}]
        exc = RequestValidationError(errors)

        with caplog.at_level(logging.WARNING, logger="app.core.handlers.validation"):
            await validation_exception_handler(mock_request, exc)

        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "Validation error" in caplog.records[0].message

    async def test_log_includes_path(self, mock_request: Request, caplog: pytest.LogCaptureFixture) -> None:
        """
        Verify log includes request path.
        """
        errors = [{"loc": ("body", "age"), "msg": "Value error", "type": "value_error"}]
        exc = RequestValidationError(errors)

        with caplog.at_level(logging.WARNING, logger="app.core.handlers.validation"):
            await validation_exception_handler(mock_request, exc)

        record = caplog.records[0]
        assert record.path == "/test/path"


class TestValidationExceptionHandlerDirect:
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
            "method": "POST",
            "path": "/test",
            "query_string": b"",
            "headers": [],
        }
        return Request(scope)

    async def test_handler_returns_422(self, mock_request: Request) -> None:
        """
        Verify handler function returns 422 status code.
        """
        errors = [{"loc": ("body", "field"), "msg": "Required", "type": "missing"}]
        exc = RequestValidationError(errors)

        response = await validation_exception_handler(mock_request, exc)

        assert response.status_code == 422

    async def test_handler_returns_errors_in_detail(self, mock_request: Request) -> None:
        """
        Verify handler includes error list in response body.
        """
        errors = [
            {"loc": ("body", "name"), "msg": "Field required", "type": "missing"},
            {"loc": ("body", "age"), "msg": "Field required", "type": "missing"},
        ]
        exc = RequestValidationError(errors)

        response = await validation_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body)
        assert "detail" in body
        assert len(body["detail"]) == 2
