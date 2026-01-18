"""
Service-layer mocks for tests.
"""

from unittest.mock import AsyncMock

from app.models.profile import Profile
from app.services.profile import ProfileService
from tests.helpers.profiles import make_profile


def create_mock_profile_service(profile: Profile | None = None) -> AsyncMock:
    """
    Create a mock ProfileService with pre-configured return values.

    Args:
        profile: Optional profile to return from service methods.
                 If None, uses make_profile() with defaults.

    Returns:
        AsyncMock configured with ProfileService spec.
    """
    mock = AsyncMock(spec=ProfileService)
    default_profile = profile or make_profile()
    mock.get_profile.return_value = default_profile
    mock.create_profile.return_value = default_profile
    mock.update_profile.return_value = default_profile
    mock.delete_profile.return_value = None
    return mock


def create_mock_profile_service_not_found() -> AsyncMock:
    """
    Create a mock ProfileService that returns None for get_profile.

    Simulates the case where a profile does not exist.
    """
    mock = AsyncMock(spec=ProfileService)
    mock.get_profile.return_value = None
    return mock
