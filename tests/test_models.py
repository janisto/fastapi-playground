"""Unit tests for profile models."""

from datetime import datetime, UTC

import pytest
from pydantic import ValidationError

from app.models.profile import Profile, ProfileCreate, ProfileResponse, ProfileUpdate


class TestProfileModels:
    """Test profile model validation."""

    def test_profile_create_valid_data(self) -> None:
        """Test creating a valid ProfileCreate instance."""
        data = {
            "firstname": "John",
            "lastname": "Doe",
            "email": "john@example.com",
            "phone_number": "+1234567890",
            "marketing": True,
            "terms": True,
        }

        profile = ProfileCreate(**data)

        assert profile.firstname == "John"
        assert profile.lastname == "Doe"
        assert profile.email == "john@example.com"
        assert profile.phone_number == "+1234567890"
        assert profile.marketing is True
        assert profile.terms is True

    def test_profile_create_missing_required_fields(self) -> None:
        """Test validation error for missing required fields."""
        data = {
            "firstname": "John",
            # Missing required fields
        }

        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(**data)

        errors = exc_info.value.errors()
        error_fields = [error["loc"][0] for error in errors]

        assert "lastname" in error_fields
        assert "email" in error_fields
        assert "phone_number" in error_fields
        assert "terms" in error_fields

    def test_profile_create_invalid_email(self) -> None:
        """Test validation error for invalid email format."""
        data = {
            "firstname": "John",
            "lastname": "Doe",
            "email": "invalid-email",
            "phone_number": "+1234567890",
            "marketing": True,
            "terms": True,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(**data)

        errors = exc_info.value.errors()
        assert any(error["loc"][0] == "email" for error in errors)

    def test_profile_create_empty_strings(self) -> None:
        """Test validation error for empty string fields."""
        data = {
            "firstname": "",  # Empty string
            "lastname": "Doe",
            "email": "john@example.com",
            "phone_number": "",  # Empty string
            "marketing": True,
            "terms": True,
        }

        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(**data)

        errors = exc_info.value.errors()
        error_fields = [error["loc"][0] for error in errors]

        assert "firstname" in error_fields
        assert "phone_number" in error_fields

    def test_profile_update_partial_data(self) -> None:
        """Test ProfileUpdate with partial data."""
        data = {"firstname": "Jane", "marketing": False}

        profile_update = ProfileUpdate(**data)

        assert profile_update.firstname == "Jane"
        assert profile_update.marketing is False
        assert profile_update.lastname is None
        assert profile_update.email is None

    def test_profile_update_empty_data(self) -> None:
        """Test ProfileUpdate with no data."""
        profile_update = ProfileUpdate()

        assert profile_update.firstname is None
        assert profile_update.lastname is None
        assert profile_update.email is None
        assert profile_update.phone_number is None
        assert profile_update.marketing is None
        assert profile_update.terms is None

    def test_profile_complete_model(self) -> None:
        """Test complete Profile model."""
        now = datetime.now(UTC)

        data = {
            "id": "user-123",
            "firstname": "John",
            "lastname": "Doe",
            "email": "john@example.com",
            "phone_number": "+1234567890",
            "marketing": True,
            "terms": True,
            "created_at": now,
            "updated_at": now,
        }

        profile = Profile(**data)

        assert profile.id == "user-123"
        assert profile.firstname == "John"
        assert profile.created_at == now
        assert profile.updated_at == now

    def test_profile_response_model(self) -> None:
        """Test ProfileResponse model."""
        now = datetime.now(UTC)

        profile_data = {
            "id": "user-123",
            "firstname": "John",
            "lastname": "Doe",
            "email": "john@example.com",
            "phone_number": "+1234567890",
            "marketing": True,
            "terms": True,
            "created_at": now,
            "updated_at": now,
        }

        profile = Profile(**profile_data)

        response = ProfileResponse(success=True, message="Profile retrieved successfully", profile=profile)

        assert response.success is True
        assert response.message == "Profile retrieved successfully"
        assert response.profile.firstname == "John"

    def test_profile_response_without_profile(self) -> None:
        """Test ProfileResponse without profile data."""
        response = ProfileResponse(success=False, message="Profile not found", profile=None)

        assert response.success is False
        assert response.message == "Profile not found"
        assert response.profile is None
