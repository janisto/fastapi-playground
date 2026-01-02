"""
Unit tests for health response models.
"""

import pytest
from pydantic import ValidationError

from app.models.health import HealthResponse


class TestHealthResponse:
    """
    Tests for HealthResponse model.
    """

    def test_healthy_message(self) -> None:
        """
        Verify healthy message creation.
        """
        health = HealthResponse(message="healthy")
        assert health.message == "healthy"

    def test_serialization(self) -> None:
        """
        Verify health response serializes correctly.
        """
        health = HealthResponse(message="healthy")
        data = health.model_dump()
        assert data == {"$schema": None, "message": "healthy"}

    def test_serialization_with_schema(self) -> None:
        """
        Verify health response with schema serializes correctly.
        """
        health = HealthResponse(
            schema_url="http://localhost/schemas/HealthResponse.json",
            message="healthy",
        )
        data = health.model_dump()
        assert data == {
            "$schema": "http://localhost/schemas/HealthResponse.json",
            "message": "healthy",
        }

    def test_invalid_message_raises(self) -> None:
        """
        Verify only 'healthy' literal is accepted.
        """
        with pytest.raises(ValidationError):
            HealthResponse(message="unhealthy")

    def test_json_serialization(self) -> None:
        """
        Verify health response serializes to JSON correctly.
        """
        health = HealthResponse(message="healthy")
        json_str = health.model_dump_json()
        assert '"message":"healthy"' in json_str
