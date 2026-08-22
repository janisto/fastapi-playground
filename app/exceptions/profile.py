"""Profile service boundary exceptions."""


class ProfileNotFoundError(Exception):
    """The current principal has no profile."""


class ProfileAlreadyExistsError(Exception):
    """The current principal already has a profile."""


class ProfileDependencyError(Exception):
    """A persistence result is unavailable or unconfirmed."""


class ProfileTimestampOverflowError(Exception):
    """A real mutation cannot advance the canonical timestamp domain."""
