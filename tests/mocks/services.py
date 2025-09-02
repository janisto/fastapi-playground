"""Service-layer mocks for tests."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.models.profile import Profile


def make_profile_doc(id: str = "test-user-123") -> Profile:
    now = datetime.now(UTC)
    return Profile(
        id=id,
        firstname="John",
        lastname="Doe",
        email="john@example.com",
        phone_number="+1234567890",
        marketing=True,
        terms=True,
        created_at=now,
        updated_at=now,
    )


def stub_profile_service_get_returning(profile: Profile | None) -> MagicMock:
    stub = MagicMock()
    stub.get_profile.return_value = profile
    return stub
