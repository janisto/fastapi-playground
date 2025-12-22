"""
Unit tests for error response models.
"""

from app.models.error import ErrorResponse


class TestErrorResponse:
    """
    Tests for ErrorResponse model.
    """

    def test_basic_error(self) -> None:
        """
        Verify basic error response creation.
        """
        error = ErrorResponse(detail="Something went wrong")
        assert error.detail == "Something went wrong"

    def test_serialization(self) -> None:
        """
        Verify error response serializes correctly.
        """
        error = ErrorResponse(detail="Not found")
        data = error.model_dump()
        assert data == {"detail": "Not found"}

    def test_json_serialization(self) -> None:
        """
        Verify error response serializes to JSON correctly.
        """
        error = ErrorResponse(detail="Unauthorized")
        json_str = error.model_dump_json()
        assert '"detail":"Unauthorized"' in json_str
