"""
Schema-related exceptions.
"""

from fastapi_problem.error import NotFoundProblem


class SchemaNotFoundError(NotFoundProblem):
    """
    Raised when a JSON schema cannot be found.
    """

    title = "Schema not found"
