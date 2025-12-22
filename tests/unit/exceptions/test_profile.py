"""
Unit tests for profile-related exceptions.

Note: tests/unit/models/test_profile_model.py uses a different basename to avoid
a pytest module naming conflict with this file. Pytest requires unique basenames.
"""

from app.exceptions.base import ConflictError, DomainError, NotFoundError
from app.exceptions.profile import ProfileAlreadyExistsError, ProfileNotFoundError


class TestProfileNotFoundError:
    """
    Tests for ProfileNotFoundError.
    """

    def test_status_code_is_404(self) -> None:
        """
        Verify status_code is 404.
        """
        err = ProfileNotFoundError()
        assert err.status_code == 404

    def test_default_detail(self) -> None:
        """
        Verify default detail message.
        """
        err = ProfileNotFoundError()
        assert err.detail == "Profile not found"

    def test_custom_detail(self) -> None:
        """
        Verify custom detail overrides default.
        """
        err = ProfileNotFoundError("User profile not found")
        assert err.detail == "User profile not found"

    def test_inherits_from_not_found_error(self) -> None:
        """
        Verify inheritance chain.
        """
        err = ProfileNotFoundError()
        assert isinstance(err, NotFoundError)
        assert isinstance(err, DomainError)

    def test_exception_message(self) -> None:
        """
        Verify exception message matches detail.
        """
        err = ProfileNotFoundError()
        assert str(err) == "Profile not found"


class TestProfileAlreadyExistsError:
    """
    Tests for ProfileAlreadyExistsError.
    """

    def test_status_code_is_409(self) -> None:
        """
        Verify status_code is 409.
        """
        err = ProfileAlreadyExistsError()
        assert err.status_code == 409

    def test_default_detail(self) -> None:
        """
        Verify default detail message.
        """
        err = ProfileAlreadyExistsError()
        assert err.detail == "Profile already exists"

    def test_custom_detail(self) -> None:
        """
        Verify custom detail overrides default.
        """
        err = ProfileAlreadyExistsError("Duplicate profile for user")
        assert err.detail == "Duplicate profile for user"

    def test_inherits_from_conflict_error(self) -> None:
        """
        Verify inheritance chain.
        """
        err = ProfileAlreadyExistsError()
        assert isinstance(err, ConflictError)
        assert isinstance(err, DomainError)

    def test_exception_message(self) -> None:
        """
        Verify exception message matches detail.
        """
        err = ProfileAlreadyExistsError()
        assert str(err) == "Profile already exists"
