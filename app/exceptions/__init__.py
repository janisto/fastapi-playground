"""
Domain-specific exceptions.
"""

from app.exceptions.base import (
    BadRequestProblem,
    ConflictProblem,
    ForbiddenProblem,
    NotFoundProblem,
    ServerProblem,
    UnauthorisedProblem,
    UnprocessableProblem,
)
from app.exceptions.profile import ProfileAlreadyExistsError, ProfileNotFoundError

__all__ = [
    "BadRequestProblem",
    "ConflictProblem",
    "ForbiddenProblem",
    "NotFoundProblem",
    "ProfileAlreadyExistsError",
    "ProfileNotFoundError",
    "ServerProblem",
    "UnauthorisedProblem",
    "UnprocessableProblem",
]
