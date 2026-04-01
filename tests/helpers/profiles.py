"""
Profile-related helpers for tests.
"""

from datetime import UTC, datetime

from app.models.profile import Profile, ProfileCreate, ProfileUpdate


def make_profile_create(
    firstname: str = "John",
    lastname: str = "Doe",
    email: str = "john@example.com",
    phone_number: str = "+1234567890",
    marketing: bool = True,
    terms: bool = True,
) -> ProfileCreate:
    """
    Factory for ProfileCreate with sensible defaults.
    """
    return ProfileCreate(
        firstname=firstname,
        lastname=lastname,
        email=email,
        phone_number=phone_number,
        marketing=marketing,
        terms=terms,
    )


def make_profile(
    user_id: str = "test-user-123",
    firstname: str = "John",
    lastname: str = "Doe",
    email: str = "john@example.com",
    phone_number: str = "+1234567890",
    marketing: bool = True,
    terms: bool = True,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> Profile:
    """
    Create a Profile instance for testing.
    """
    now = datetime.now(UTC)
    return Profile(
        id=user_id,
        firstname=firstname,
        lastname=lastname,
        email=email,
        phone_number=phone_number,
        marketing=marketing,
        terms=terms,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )


def make_profile_update(
    firstname: str | None = None,
    lastname: str | None = None,
    email: str | None = None,
    phone_number: str | None = None,
    marketing: bool | None = None,
) -> ProfileUpdate:
    """
    Factory for ProfileUpdate with only the provided fields.
    """
    return ProfileUpdate(
        firstname=firstname,
        lastname=lastname,
        email=email,
        phone_number=phone_number,
        marketing=marketing,
    )


def make_profile_payload_dict(
    *,
    firstname: str = "John",
    lastname: str = "Doe",
    email: str = "john@example.com",
    phone_number: str = "+1234567890",
    marketing: bool = True,
    terms: bool = True,
    overrides: dict[str, object] | None = None,
    omit: list[str] | None = None,
) -> dict[str, object]:
    """
    Build a plain dict payload for POST/PUT requests.

    Use `overrides` to change values and `omit` to drop specific keys to test validation errors.
    """
    payload: dict[str, object] = {
        "firstname": firstname,
        "lastname": lastname,
        "email": email,
        "phone_number": phone_number,
        "marketing": marketing,
        "terms": terms,
    }
    if overrides:
        payload.update(overrides)
    if omit:
        for key in omit:
            payload.pop(key, None)
    return payload
