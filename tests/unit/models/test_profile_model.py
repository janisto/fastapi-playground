"""
Unit tests for profile models.

Note: This file is named test_profile_model.py (not test_profile.py) to avoid
a pytest module naming conflict with tests/unit/exceptions/test_profile.py.
Pytest requires unique basenames across the test tree.
"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.profile import (
    PROFILE_COLLECTION,
    Profile,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
)


class TestProfileCreate:
    """
    Tests for ProfileCreate model.
    """

    def test_valid_profile_create(self) -> None:
        """
        Verify valid data creates a ProfileCreate instance.
        """
        profile = ProfileCreate(
            firstname="John",
            lastname="Doe",
            email="john@example.com",
            phone_number="+358401234567",
            marketing=True,
            terms=True,
        )
        assert profile.firstname == "John"
        assert profile.lastname == "Doe"
        assert profile.email == "john@example.com"
        assert profile.phone_number == "+358401234567"
        assert profile.marketing is True
        assert profile.terms is True

    def test_email_is_normalized(self) -> None:
        """
        Verify email is lowercased.
        """
        profile = ProfileCreate(
            firstname="John",
            lastname="Doe",
            email="JOHN@EXAMPLE.COM",
            phone_number="+358401234567",
            terms=True,
        )
        assert profile.email == "john@example.com"

    def test_marketing_defaults_to_false(self) -> None:
        """
        Verify marketing field defaults to False.
        """
        profile = ProfileCreate(
            firstname="John",
            lastname="Doe",
            email="john@example.com",
            phone_number="+358401234567",
            terms=True,
        )
        assert profile.marketing is False

    @pytest.mark.parametrize(
        "missing_field",
        ["firstname", "lastname", "email", "phone_number", "terms"],
    )
    def test_missing_required_field_raises(self, missing_field: str) -> None:
        """
        Verify missing required fields raise ValidationError.
        """
        data = {
            "firstname": "John",
            "lastname": "Doe",
            "email": "john@example.com",
            "phone_number": "+358401234567",
            "terms": True,
        }
        del data[missing_field]

        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(**data)

        errors = exc_info.value.errors()
        assert any(missing_field in str(err["loc"]) for err in errors)

    def test_extra_fields_forbidden(self) -> None:
        """
        Verify extra fields are rejected.
        """
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(
                firstname="John",
                lastname="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                terms=True,
                extra_field="not allowed",
            )

        errors = exc_info.value.errors()
        assert any("extra" in str(err["type"]) for err in errors)

    def test_invalid_email_raises(self) -> None:
        """
        Verify invalid email format raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                firstname="John",
                lastname="Doe",
                email="not-an-email",
                phone_number="+358401234567",
                terms=True,
            )

    def test_invalid_phone_raises(self) -> None:
        """
        Verify invalid phone format raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                firstname="John",
                lastname="Doe",
                email="john@example.com",
                phone_number="invalid-phone",
                terms=True,
            )

    def test_empty_firstname_raises(self) -> None:
        """
        Verify empty firstname raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                firstname="",
                lastname="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                terms=True,
            )

    def test_empty_lastname_raises(self) -> None:
        """
        Verify empty lastname raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                firstname="John",
                lastname="",
                email="john@example.com",
                phone_number="+358401234567",
                terms=True,
            )

    def test_firstname_max_length_raises(self) -> None:
        """
        Verify firstname exceeding max length raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                firstname="J" * 101,
                lastname="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                terms=True,
            )

    def test_lastname_max_length_raises(self) -> None:
        """
        Verify lastname exceeding max length raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                firstname="John",
                lastname="D" * 101,
                email="john@example.com",
                phone_number="+358401234567",
                terms=True,
            )


class TestProfileUpdate:
    """
    Tests for ProfileUpdate model (partial updates).
    """

    def test_all_fields_optional(self) -> None:
        """
        Verify all fields are optional for partial updates.
        """
        profile = ProfileUpdate()
        assert profile.firstname is None
        assert profile.lastname is None
        assert profile.email is None
        assert profile.phone_number is None
        assert profile.marketing is None
        assert profile.terms is None

    def test_partial_update(self) -> None:
        """
        Verify partial updates work correctly.
        """
        profile = ProfileUpdate(firstname="Jane")
        assert profile.firstname == "Jane"
        assert profile.lastname is None

    def test_email_is_normalized(self) -> None:
        """
        Verify email is lowercased when provided.
        """
        profile = ProfileUpdate(email="JANE@EXAMPLE.COM")
        assert profile.email == "jane@example.com"

    def test_extra_fields_forbidden(self) -> None:
        """
        Verify extra fields are rejected.
        """
        with pytest.raises(ValidationError):
            ProfileUpdate(extra_field="not allowed")

    def test_model_dump_exclude_unset(self) -> None:
        """
        Verify model_dump with exclude_unset only returns set fields.
        """
        profile = ProfileUpdate(firstname="Jane")
        dumped = profile.model_dump(exclude_unset=True)
        assert dumped == {"firstname": "Jane"}

    def test_invalid_email_raises(self) -> None:
        """
        Verify invalid email format raises ValidationError when provided.
        """
        with pytest.raises(ValidationError):
            ProfileUpdate(email="not-an-email")

    def test_invalid_phone_raises(self) -> None:
        """
        Verify invalid phone format raises ValidationError when provided.
        """
        with pytest.raises(ValidationError):
            ProfileUpdate(phone_number="invalid-phone")

    def test_empty_firstname_raises(self) -> None:
        """
        Verify empty firstname raises ValidationError when provided.
        """
        with pytest.raises(ValidationError):
            ProfileUpdate(firstname="")

    def test_firstname_max_length_raises(self) -> None:
        """
        Verify firstname exceeding max length raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileUpdate(firstname="J" * 101)


class TestProfile:
    """
    Tests for complete Profile model with metadata.
    """

    def test_valid_profile(self) -> None:
        """
        Verify valid data creates a Profile instance.
        """
        now = datetime.now(UTC)
        profile = Profile(
            id="user-123",
            firstname="John",
            lastname="Doe",
            email="john@example.com",
            phone_number="+358401234567",
            marketing=True,
            terms=True,
            created_at=now,
            updated_at=now,
        )
        assert profile.id == "user-123"
        assert profile.created_at == now
        assert profile.updated_at == now

    def test_missing_id_raises(self) -> None:
        """
        Verify missing id raises ValidationError.
        """
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            Profile(
                firstname="John",
                lastname="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                marketing=True,
                terms=True,
                created_at=now,
                updated_at=now,
            )

    def test_missing_timestamps_raises(self) -> None:
        """
        Verify missing timestamps raise ValidationError.
        """
        with pytest.raises(ValidationError):
            Profile(
                id="user-123",
                firstname="John",
                lastname="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                marketing=True,
                terms=True,
            )

    def test_id_max_length_raises(self) -> None:
        """
        Verify id exceeding max length raises ValidationError.
        """
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            Profile(
                id="x" * 129,
                firstname="John",
                lastname="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                marketing=True,
                terms=True,
                created_at=now,
                updated_at=now,
            )


class TestProfileResponse:
    """
    Tests for ProfileResponse model.
    """

    def test_success_with_profile(self) -> None:
        """
        Verify response with profile data.
        """
        now = datetime.now(UTC)
        profile = Profile(
            id="user-123",
            firstname="John",
            lastname="Doe",
            email="john@example.com",
            phone_number="+358401234567",
            marketing=True,
            terms=True,
            created_at=now,
            updated_at=now,
        )
        response = ProfileResponse(
            success=True,
            message="Profile created",
            profile=profile,
        )
        assert response.success is True
        assert response.profile is not None
        assert response.profile.id == "user-123"

    def test_success_without_profile(self) -> None:
        """
        Verify response without profile data.
        """
        response = ProfileResponse(
            success=True,
            message="Profile deleted",
            profile=None,
        )
        assert response.success is True
        assert response.profile is None

    def test_failure_response(self) -> None:
        """
        Verify failure response with success=False.
        """
        response = ProfileResponse(
            success=False,
            message="Profile not found",
            profile=None,
        )
        assert response.success is False
        assert response.message == "Profile not found"

    def test_json_serialization(self) -> None:
        """
        Verify response serializes to JSON correctly.
        """
        now = datetime.now(UTC)
        profile = Profile(
            id="user-123",
            firstname="John",
            lastname="Doe",
            email="john@example.com",
            phone_number="+358401234567",
            marketing=True,
            terms=True,
            created_at=now,
            updated_at=now,
        )
        response = ProfileResponse(
            success=True,
            message="Profile retrieved",
            profile=profile,
        )
        json_str = response.model_dump_json()
        assert '"success":true' in json_str
        assert '"message":"Profile retrieved"' in json_str
        assert '"id":"user-123"' in json_str


class TestProfileCollection:
    """
    Tests for PROFILE_COLLECTION constant.
    """

    def test_collection_name(self) -> None:
        """
        Verify the Firestore collection name.
        """
        assert PROFILE_COLLECTION == "profiles"
