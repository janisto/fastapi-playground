"""
Unit tests for profile-related exceptions.

Note: tests/unit/models/test_profile_model.py uses a different basename to avoid
a pytest module naming conflict with this file. Pytest requires unique basenames.
"""

from fastapi_problem.error import ConflictProblem, NotFoundProblem, Problem

from app.exceptions.profile import ProfileAlreadyExistsError, ProfileNotFoundError


class TestProfileNotFoundError:
    """
    Tests for ProfileNotFoundError.
    """

    def test_status_is_404(self) -> None:
        """
        Verify status is 404.
        """
        err = ProfileNotFoundError()
        assert err.status == 404

    def test_default_title(self) -> None:
        """
        Verify default title message.
        """
        err = ProfileNotFoundError()
        assert err.title == "Profile not found"

    def test_inherits_from_not_found_problem(self) -> None:
        """
        Verify inheritance chain.
        """
        err = ProfileNotFoundError()
        assert isinstance(err, NotFoundProblem)
        assert isinstance(err, Problem)

    def test_custom_detail(self) -> None:
        """
        Verify custom detail can be set.
        """
        err = ProfileNotFoundError(detail="User profile not found")
        assert err.detail == "User profile not found"


class TestProfileAlreadyExistsError:
    """
    Tests for ProfileAlreadyExistsError.
    """

    def test_status_is_409(self) -> None:
        """
        Verify status is 409.
        """
        err = ProfileAlreadyExistsError()
        assert err.status == 409

    def test_default_title(self) -> None:
        """
        Verify default title message.
        """
        err = ProfileAlreadyExistsError()
        assert err.title == "Profile already exists"

    def test_inherits_from_conflict_problem(self) -> None:
        """
        Verify inheritance chain.
        """
        err = ProfileAlreadyExistsError()
        assert isinstance(err, ConflictProblem)
        assert isinstance(err, Problem)

    def test_custom_detail(self) -> None:
        """
        Verify custom detail can be set.
        """
        err = ProfileAlreadyExistsError(detail="Duplicate profile for user")
        assert err.detail == "Duplicate profile for user"
