"""
Unit tests for app/dependencies.py.
"""

from app.dependencies import (
    CurrentUser,
    FirebaseUser,
    ProfileService,
    ProfileServiceDep,
    get_profile_service,
)


class TestGetProfileService:
    """Tests for the get_profile_service dependency provider."""

    def test_returns_profile_service_instance(self) -> None:
        """Verify the factory returns a ProfileService instance."""
        result = get_profile_service()

        assert isinstance(result, ProfileService)

    def test_returns_new_instance_each_call(self) -> None:
        """Verify each call creates a new instance (not singleton)."""
        first = get_profile_service()
        second = get_profile_service()

        assert first is not second


class TestExports:
    """Tests for module exports."""

    def test_current_user_is_exported(self) -> None:
        """Verify CurrentUser type alias is accessible."""
        assert CurrentUser is not None

    def test_firebase_user_is_exported(self) -> None:
        """Verify FirebaseUser is re-exported."""
        assert FirebaseUser is not None

    def test_profile_service_is_exported(self) -> None:
        """Verify ProfileService is re-exported."""
        assert ProfileService is not None

    def test_profile_service_dep_is_exported(self) -> None:
        """Verify ProfileServiceDep type alias is accessible."""
        assert ProfileServiceDep is not None
