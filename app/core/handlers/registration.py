"""
Exception handler registration.
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.handlers.domain import domain_exception_handler
from app.core.handlers.http import http_exception_handler
from app.core.handlers.validation import validation_exception_handler
from app.exceptions import DomainError


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI app.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(DomainError, domain_exception_handler)
