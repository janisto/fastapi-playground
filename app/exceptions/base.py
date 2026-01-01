"""
Domain exception base classes using fastapi-problem.
"""

from fastapi_problem.error import (
    BadRequestProblem,
    ConflictProblem,
    ForbiddenProblem,
    NotFoundProblem,
    ServerProblem,
    UnauthorisedProblem,
    UnprocessableProblem,
)

__all__ = [
    "BadRequestProblem",
    "ConflictProblem",
    "ForbiddenProblem",
    "NotFoundProblem",
    "ServerProblem",
    "UnauthorisedProblem",
    "UnprocessableProblem",
]
