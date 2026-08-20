"""
Domain-specific exceptions.
"""

from app.exceptions.profile import (
    ProfileAlreadyExistsError,
    ProfileDependencyError,
    ProfileNotFoundError,
    ProfileTimestampOverflowError,
)

__all__ = [
    "ProfileAlreadyExistsError",
    "ProfileDependencyError",
    "ProfileNotFoundError",
    "ProfileTimestampOverflowError",
]
