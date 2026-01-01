"""
Profile-related exceptions.
"""

from fastapi_problem.error import ConflictProblem, NotFoundProblem


class ProfileNotFoundError(NotFoundProblem):
    """
    Raised when a profile cannot be found.
    """

    title = "Profile not found"


class ProfileAlreadyExistsError(ConflictProblem):
    """
    Raised when attempting to create a duplicate profile.
    """

    title = "Profile already exists"
