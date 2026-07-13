"""
Domain-specific exceptions.
"""

from app.exceptions.profile import ProfileAlreadyExistsError, ProfileNotFoundError
from app.exceptions.schema import SchemaNotFoundError

__all__ = [
    "ProfileAlreadyExistsError",
    "ProfileNotFoundError",
    "SchemaNotFoundError",
]
