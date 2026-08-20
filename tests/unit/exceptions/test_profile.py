"""Unit tests for transport-independent profile service outcomes."""

import pytest

from app.exceptions.profile import (
    ProfileAlreadyExistsError,
    ProfileDependencyError,
    ProfileNotFoundError,
    ProfileTimestampOverflowError,
)


@pytest.mark.parametrize(
    "error_type",
    [
        ProfileAlreadyExistsError,
        ProfileDependencyError,
        ProfileNotFoundError,
        ProfileTimestampOverflowError,
    ],
)
def test_profile_service_outcomes_are_plain_domain_exceptions(error_type: type[Exception]) -> None:
    error = error_type()
    assert isinstance(error, Exception)
    assert not hasattr(error, "status")
