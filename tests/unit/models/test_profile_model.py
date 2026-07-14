"""
Unit tests for profile models.

Note: This file is named test_profile_model.py (not test_profile.py) to avoid
a pytest module naming conflict with tests/unit/exceptions/test_profile.py.
Pytest requires unique basenames across the test tree.
"""

from datetime import UTC, datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError

from app.models.profile import (
    PROFILE_COLLECTION,
    Profile,
    ProfileCreate,
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
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="+358401234567",
            marketing=True,
            terms=True,
        )
        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
        assert profile.email == "john@example.com"
        assert profile.phone_number == "+358401234567"
        assert profile.marketing is True
        assert profile.terms is True

    def test_email_is_normalized(self) -> None:
        """
        Verify email is lowercased.
        """
        profile = ProfileCreate(
            first_name="John",
            last_name="Doe",
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
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="+358401234567",
            terms=True,
        )
        assert profile.marketing is False

    @pytest.mark.parametrize(
        "missing_field",
        ["first_name", "last_name", "email", "phone_number", "terms"],
    )
    def test_missing_required_field_raises(self, missing_field: str) -> None:
        """
        Verify missing required fields raise ValidationError.
        """
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone_number": "+358401234567",
            "terms": True,
        }
        del data[missing_field]

        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(**cast("Any", data))

        errors = exc_info.value.errors()
        assert any(missing_field in str(err["loc"]) for err in errors)

    def test_extra_fields_forbidden(self) -> None:
        """
        Verify extra fields are rejected.
        """
        with pytest.raises(ValidationError) as exc_info:
            cast("Any", ProfileCreate)(
                first_name="John",
                last_name="Doe",
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
                first_name="John",
                last_name="Doe",
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
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                phone_number="invalid-phone",
                terms=True,
            )

    def test_empty_first_name_raises(self) -> None:
        """
        Verify empty first_name raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                first_name="",
                last_name="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                terms=True,
            )

    def test_empty_last_name_raises(self) -> None:
        """
        Verify empty last_name raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                first_name="John",
                last_name="",
                email="john@example.com",
                phone_number="+358401234567",
                terms=True,
            )

    def test_first_name_max_length_raises(self) -> None:
        """
        Verify first_name exceeding max length raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                first_name="J" * 101,
                last_name="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                terms=True,
            )

    def test_last_name_max_length_raises(self) -> None:
        """
        Verify last_name exceeding max length raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileCreate(
                first_name="John",
                last_name="D" * 101,
                email="john@example.com",
                phone_number="+358401234567",
                terms=True,
            )

    def test_terms_false_raises_validation_error(self) -> None:
        """
        Verify terms=False raises ValidationError on profile creation.
        """
        with pytest.raises(ValidationError) as exc_info:
            ProfileCreate(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                terms=False,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("terms",)
        assert "terms must be accepted" in errors[0]["msg"]
        assert errors[0]["type"] == "value_error"

    def test_terms_true_accepted(self) -> None:
        """
        Verify terms=True is accepted on profile creation.
        """
        profile = ProfileCreate(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone_number="+358401234567",
            terms=True,
        )
        assert profile.terms is True


class TestProfileUpdate:
    """
    Tests for ProfileUpdate model (partial updates).
    """

    def test_all_fields_can_be_omitted(self) -> None:
        """
        Verify all fields can be omitted for partial updates.
        """
        profile = ProfileUpdate()
        assert profile.model_dump() == {}

    def test_partial_update(self) -> None:
        """
        Verify partial updates work correctly.
        """
        profile = ProfileUpdate(first_name="Jane")
        assert profile.first_name == "Jane"
        assert profile.model_dump() == {"first_name": "Jane"}

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
            cast("Any", ProfileUpdate)(extra_field="not allowed")

    def test_model_dump_exclude_unset(self) -> None:
        """
        Verify model_dump with exclude_unset only returns set fields.
        """
        profile = ProfileUpdate(first_name="Jane")
        dumped = profile.model_dump(exclude_unset=True)
        assert dumped == {"first_name": "Jane"}

    @pytest.mark.parametrize("field", ["first_name", "last_name", "email", "phone_number", "marketing"])
    def test_explicit_null_is_rejected(self, field: str) -> None:
        """
        Verify null cannot silently become an omitted partial update.
        """
        with pytest.raises(ValidationError):
            ProfileUpdate.model_validate({field: None})

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

    def test_empty_first_name_raises(self) -> None:
        """
        Verify empty first_name raises ValidationError when provided.
        """
        with pytest.raises(ValidationError):
            ProfileUpdate(first_name="")

    def test_first_name_max_length_raises(self) -> None:
        """
        Verify first_name exceeding max length raises ValidationError.
        """
        with pytest.raises(ValidationError):
            ProfileUpdate(first_name="J" * 101)


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
            first_name="John",
            last_name="Doe",
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
            Profile.model_validate(
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com",
                    "phone_number": "+358401234567",
                    "marketing": True,
                    "terms": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )

    def test_missing_timestamps_raises(self) -> None:
        """
        Verify missing timestamps raise ValidationError.
        """
        with pytest.raises(ValidationError):
            Profile.model_validate(
                {
                    "id": "user-123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com",
                    "phone_number": "+358401234567",
                    "marketing": True,
                    "terms": True,
                }
            )

    def test_id_max_length_raises(self) -> None:
        """
        Verify id exceeding max length raises ValidationError.
        """
        now = datetime.now(UTC)
        with pytest.raises(ValidationError):
            Profile(
                id="x" * 129,
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                phone_number="+358401234567",
                marketing=True,
                terms=True,
                created_at=now,
                updated_at=now,
            )


class TestProfileCollection:
    """
    Tests for PROFILE_COLLECTION constant.
    """

    def test_collection_name(self) -> None:
        """
        Verify the Firestore collection name.
        """
        assert PROFILE_COLLECTION == "profiles"
