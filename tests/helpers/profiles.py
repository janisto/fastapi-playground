"""Profile-related helpers for tests."""

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
    return ProfileCreate(
        firstname=firstname,
        lastname=lastname,
        email=email,
        phone_number=phone_number,
        marketing=marketing,
        terms=terms,
    )


def make_profile(
    id: str = "test-user-123",
    **kwargs: object,
) -> Profile:
    now = datetime.now(UTC)
    base = dict(
        firstname="John",
        lastname="Doe",
        email="john@example.com",
        phone_number="+1234567890",
        marketing=True,
        terms=True,
        created_at=now,
        updated_at=now,
    )
    return Profile(id=id, **{**base, **kwargs})


def make_profile_update(**kwargs: object) -> ProfileUpdate:
    return ProfileUpdate(**kwargs)


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
    """Build a plain dict payload for POST/PUT requests.

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
