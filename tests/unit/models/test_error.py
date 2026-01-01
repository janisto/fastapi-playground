"""
Unit tests for RFC 9457 Problem Details error models.
"""

from app.models.error import ProblemResponse, ValidationErrorDetail, ValidationProblemResponse


class TestProblemResponse:
    """
    Tests for ProblemResponse model.

    Per RFC 9457, the 'type' field defaults to 'about:blank' when not present,
    so we omit it from the model. The $schema field provides JSON Schema reference.
    """

    def test_basic_problem(self) -> None:
        """
        Verify basic problem response creation.
        """
        problem = ProblemResponse(title="Not Found", status=404, detail="Profile not found")
        assert problem.title == "Not Found"
        assert problem.status == 404
        assert problem.detail == "Profile not found"
        assert problem.schema_url is None

    def test_problem_with_schema(self) -> None:
        """
        Verify problem response with $schema URL.
        """
        problem = ProblemResponse(
            title="Not Found",
            status=404,
            detail="Profile not found",
            schema_url="http://example.com/schemas/ErrorModel.json",
        )
        assert problem.schema_url == "http://example.com/schemas/ErrorModel.json"

    def test_serialization(self) -> None:
        """
        Verify problem response serializes correctly with alias.
        """
        problem = ProblemResponse(title="Not Found", status=404, detail="Profile not found")
        data = problem.model_dump()
        # With serialize_by_alias=True, $schema alias is used by default
        assert data == {
            "$schema": None,
            "title": "Not Found",
            "status": 404,
            "detail": "Profile not found",
        }

    def test_serialization_by_alias(self) -> None:
        """
        Verify problem response serializes with $schema alias by default.

        With serialize_by_alias=True in model_config, aliases are used
        automatically without needing by_alias=True parameter.
        """
        problem = ProblemResponse(
            title="Not Found",
            status=404,
            detail="Profile not found",
            schema_url="http://example.com/schemas/ErrorModel.json",
        )
        # No need for by_alias=True - serialize_by_alias=True is set in model_config
        data = problem.model_dump()
        assert "$schema" in data
        assert data["$schema"] == "http://example.com/schemas/ErrorModel.json"

    def test_json_serialization(self) -> None:
        """
        Verify problem response serializes to JSON correctly.
        """
        problem = ProblemResponse(title="Unauthorized", status=401, detail="Missing token")
        json_str = problem.model_dump_json()
        assert '"title":"Unauthorized"' in json_str
        assert '"status":401' in json_str


class TestValidationErrorDetail:
    """
    Tests for ValidationErrorDetail model.
    """

    def test_basic_error(self) -> None:
        """
        Verify basic validation error creation.
        """
        error = ValidationErrorDetail(location="body.email", message="Invalid email")
        assert error.location == "body.email"
        assert error.message == "Invalid email"
        assert error.value is None

    def test_error_with_value(self) -> None:
        """
        Verify validation error with value.
        """
        error = ValidationErrorDetail(location="body.age", message="Must be positive", value=-5)
        assert error.location == "body.age"
        assert error.message == "Must be positive"
        assert error.value == -5


class TestValidationProblemResponse:
    """
    Tests for ValidationProblemResponse model.

    Uses default title 'Unprocessable Entity' and detail 'validation failed'
    per RFC 9457 when type is about:blank.
    """

    def test_basic_validation_problem(self) -> None:
        """
        Verify validation problem response creation with defaults.
        """
        problem = ValidationProblemResponse(
            errors=[
                ValidationErrorDetail(location="body.email", message="Invalid email"),
            ],
        )
        assert problem.title == "Unprocessable Entity"
        assert problem.status == 422
        assert problem.detail == "validation failed"
        assert len(problem.errors) == 1
        assert problem.errors[0].location == "body.email"

    def test_validation_problem_with_schema(self) -> None:
        """
        Verify validation problem with $schema URL.
        """
        problem = ValidationProblemResponse(
            schema_url="http://example.com/schemas/ErrorModel.json",
            errors=[],
        )
        assert problem.schema_url == "http://example.com/schemas/ErrorModel.json"

    def test_serialization(self) -> None:
        """
        Verify validation problem response serializes correctly with alias.
        """
        problem = ValidationProblemResponse(errors=[])
        data = problem.model_dump()
        # With serialize_by_alias=True, $schema alias is used by default
        assert "$schema" in data
        assert "errors" in data
        assert isinstance(data["errors"], list)
        assert data["title"] == "Unprocessable Entity"
        assert data["status"] == 422
        assert data["detail"] == "validation failed"
