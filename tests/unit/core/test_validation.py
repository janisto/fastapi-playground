"""
Unit tests for validation error handler.
"""

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.exceptions import RequestValidationError
from rfc9457 import Problem

from app.core.validation import (
    SENSITIVE_FIELD_NAMES,
    is_sensitive_field,
    loc_to_dot_notation,
    validation_error_handler,
)


class TestLocToDotNotation:
    """Tests for loc_to_dot_notation function."""

    def test_simple_body_field(self) -> None:
        """Simple body.field location."""
        result = loc_to_dot_notation(("body", "email"))
        assert result == "body.email"

    def test_nested_field(self) -> None:
        """Nested field location."""
        result = loc_to_dot_notation(("body", "user", "name"))
        assert result == "body.user.name"

    def test_array_index(self) -> None:
        """Array index in location."""
        result = loc_to_dot_notation(("body", "items", 0, "name"))
        assert result == "body.items[0].name"

    def test_multiple_array_indices(self) -> None:
        """Multiple array indices in location."""
        result = loc_to_dot_notation(("body", "matrix", 0, 1))
        assert result == "body.matrix[0][1]"

    def test_query_param(self) -> None:
        """Query parameter location."""
        result = loc_to_dot_notation(("query", "page"))
        assert result == "query.page"

    def test_single_element(self) -> None:
        """Single element location."""
        result = loc_to_dot_notation(("body",))
        assert result == "body"

    def test_empty_location(self) -> None:
        """Empty location returns empty string."""
        result = loc_to_dot_notation(())
        assert result == ""

    def test_integer_first_element(self) -> None:
        """Integer as first element (edge case)."""
        result = loc_to_dot_notation((0, "name"))
        assert result == "[0].name"

    def test_deep_nested_with_indices(self) -> None:
        """Deep nesting with mixed types."""
        result = loc_to_dot_notation(("body", "data", 0, "items", 1, "value"))
        assert result == "body.data[0].items[1].value"


class TestIsSensitiveField:
    """Tests for is_sensitive_field function."""

    @pytest.mark.parametrize(
        "field_name",
        list(SENSITIVE_FIELD_NAMES),
    )
    def test_sensitive_fields_detected(self, field_name: str) -> None:
        """All sensitive field names are detected."""
        assert is_sensitive_field(("body", field_name)) is True

    @pytest.mark.parametrize(
        "field_name",
        list(SENSITIVE_FIELD_NAMES),
    )
    def test_sensitive_fields_case_insensitive(self, field_name: str) -> None:
        """Sensitive field detection is case-insensitive."""
        assert is_sensitive_field(("body", field_name.upper())) is True
        assert is_sensitive_field(("body", field_name.capitalize())) is True

    def test_non_sensitive_field(self) -> None:
        """Non-sensitive fields return False."""
        assert is_sensitive_field(("body", "email")) is False
        assert is_sensitive_field(("body", "name")) is False
        assert is_sensitive_field(("body", "id")) is False

    def test_sensitive_in_nested_path(self) -> None:
        """Sensitive field detected in nested path."""
        assert is_sensitive_field(("body", "user", "password")) is True
        assert is_sensitive_field(("body", "credentials", "api_key")) is True

    def test_integer_in_path_ignored(self) -> None:
        """Integer segments are ignored."""
        assert is_sensitive_field(("body", "items", 0, "password")) is True
        assert is_sensitive_field(("body", "items", 0, "email")) is False


class TestValidationErrorHandler:
    """Tests for validation_error_handler function."""

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create mock request with base_url for $schema generation."""
        mock = MagicMock()
        mock.base_url = "http://testserver/"
        return mock

    @pytest.fixture
    def mock_eh(self) -> MagicMock:
        """Create mock exception handler."""
        return MagicMock()

    def _make_validation_error(
        self,
        errors: list[dict[str, Any]],
    ) -> RequestValidationError:
        """Create a RequestValidationError with given errors."""
        return RequestValidationError(errors=errors)

    def test_returns_problem_with_correct_fields(
        self,
        mock_eh: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Returns Problem with correct title, status, and detail per RFC 9457."""
        errors = [
            {
                "type": "string_type",
                "loc": ("body", "name"),
                "msg": "Field required",
                "input": None,
            }
        ]
        exc = self._make_validation_error(errors)

        result = validation_error_handler(mock_eh, mock_request, exc)

        assert isinstance(result, Problem)
        assert result.title == "Unprocessable Entity"
        assert result.status == 422
        assert result.detail == "validation failed"
        assert result.extras["$schema"] == "http://testserver/schemas/ErrorModel.json"

    def test_includes_error_location_and_message(
        self,
        mock_eh: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Error includes location and message."""
        errors = [
            {
                "type": "string_type",
                "loc": ("body", "email"),
                "msg": "value is not a valid email address",
                "input": "invalid",
            }
        ]
        exc = self._make_validation_error(errors)

        result = validation_error_handler(mock_eh, mock_request, exc)

        result_errors = result.extras["errors"]
        assert len(result_errors) == 1
        error = result_errors[0]
        assert error["location"] == "body.email"
        assert error["message"] == "value is not a valid email address"
        assert error["value"] == "invalid"

    def test_redacts_sensitive_field_values(
        self,
        mock_eh: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Sensitive field values are not included in errors."""
        errors = [
            {
                "type": "string_too_short",
                "loc": ("body", "password"),
                "msg": "String should have at least 8 characters",
                "input": "secret123",
            }
        ]
        exc = self._make_validation_error(errors)

        result = validation_error_handler(mock_eh, mock_request, exc)

        result_errors = result.extras["errors"]
        assert len(result_errors) == 1
        error = result_errors[0]
        assert error["location"] == "body.password"
        assert error["message"] == "String should have at least 8 characters"
        assert "value" not in error

    def test_redacts_nested_sensitive_fields(
        self,
        mock_eh: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Nested sensitive fields are redacted."""
        errors = [
            {
                "type": "string_type",
                "loc": ("body", "user", "api_key"),
                "msg": "Field required",
                "input": "my-secret-key",
            }
        ]
        exc = self._make_validation_error(errors)

        result = validation_error_handler(mock_eh, mock_request, exc)

        assert "value" not in result.extras["errors"][0]

    def test_multiple_errors(
        self,
        mock_eh: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Multiple validation errors are included."""
        errors = [
            {
                "type": "string_type",
                "loc": ("body", "email"),
                "msg": "value is not a valid email address",
                "input": "invalid",
            },
            {
                "type": "missing",
                "loc": ("body", "name"),
                "msg": "Field required",
                "input": None,
            },
        ]
        exc = self._make_validation_error(errors)

        result = validation_error_handler(mock_eh, mock_request, exc)

        assert len(result.extras["errors"]) == 2

    def test_array_index_in_location(
        self,
        mock_eh: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Array indices in location are formatted correctly."""
        errors = [
            {
                "type": "string_type",
                "loc": ("body", "items", 0, "name"),
                "msg": "Field required",
                "input": None,
            }
        ]
        exc = self._make_validation_error(errors)

        result = validation_error_handler(mock_eh, mock_request, exc)

        assert result.extras["errors"][0]["location"] == "body.items[0].name"

    def test_error_without_input(
        self,
        mock_eh: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Error without 'input' key is handled."""
        errors = [
            {
                "type": "missing",
                "loc": ("body", "name"),
                "msg": "Field required",
            }
        ]
        exc = self._make_validation_error(errors)

        result = validation_error_handler(mock_eh, mock_request, exc)

        assert "value" not in result.extras["errors"][0]
