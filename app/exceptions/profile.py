"""
Profile-related exceptions.
"""

from app.exceptions.base import ConflictError, NotFoundError


class ProfileNotFoundError(NotFoundError):
    """
    Raised when a profile cannot be found.
    """

    detail = "Profile not found"


class ProfileAlreadyExistsError(ConflictError):
    """
    Raised when attempting to create a duplicate profile.
    """

    detail = "Profile already exists"
