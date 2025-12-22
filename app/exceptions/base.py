"""
Base exception classes with HTTP semantics.
"""


class DomainError(Exception):
    """
    Base for all domain exceptions with HTTP semantics.

    Supports optional headers for cases like rate limiting (Retry-After).
    """

    status_code: int = 500
    detail: str = "Internal error"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None, headers: dict[str, str] | None = None) -> None:
        self.detail = detail or self.__class__.detail
        self.headers = headers
        super().__init__(self.detail)


class NotFoundError(DomainError):
    """
    Base for resource not found errors.
    """

    status_code = 404
    detail = "Resource not found"


class ConflictError(DomainError):
    """
    Base for resource conflict errors.
    """

    status_code = 409
    detail = "Resource conflict"
