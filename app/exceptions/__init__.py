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
from app.exceptions.schema import SchemaNotFoundError

__all__ = [
    "BadRequestProblem",
    "ConflictProblem",
    "ForbiddenProblem",
    "NotFoundProblem",
    "ProfileAlreadyExistsError",
    "ProfileNotFoundError",
    "SchemaNotFoundError",
    "ServerProblem",
    "UnauthorisedProblem",
    "UnprocessableProblem",
]
