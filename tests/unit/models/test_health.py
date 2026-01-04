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

    def test_healthy_status(self) -> None:
        """
        Verify healthy status creation.
        """
        health = HealthResponse(status="healthy")
        assert health.status == "healthy"

    def test_serialization(self) -> None:
        """
        Verify health response serializes correctly.
        """
        health = HealthResponse(status="healthy")
        data = health.model_dump()
        assert data == {"$schema": None, "status": "healthy"}

    def test_serialization_with_schema(self) -> None:
        """
        Verify health response with schema serializes correctly.
        """
        health = HealthResponse(
            schema_url="http://localhost/schemas/HealthResponse.json",
            status="healthy",
        )
        data = health.model_dump()
        assert data == {
            "$schema": "http://localhost/schemas/HealthResponse.json",
            "status": "healthy",
        }

    def test_invalid_status_raises(self) -> None:
        """
        Verify only 'healthy' literal is accepted.
        """
        with pytest.raises(ValidationError):
            HealthResponse(status="unhealthy")

    def test_json_serialization(self) -> None:
        """
        Verify health response serializes to JSON correctly.
        """
        health = HealthResponse(status="healthy")
        json_str = health.model_dump_json()
        assert '"status":"healthy"' in json_str
