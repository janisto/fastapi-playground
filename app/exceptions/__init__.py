"""
Domain-specific exceptions.
"""

from app.exceptions.base import ConflictError, DomainError, NotFoundError
from app.exceptions.profile import ProfileAlreadyExistsError, ProfileNotFoundError

__all__ = [
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "ProfileAlreadyExistsError",
    "ProfileNotFoundError",
]
