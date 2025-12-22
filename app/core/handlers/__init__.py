"""
Application-wide exception handlers.
"""

from app.core.handlers.domain import domain_exception_handler
from app.core.handlers.http import http_exception_handler
from app.core.handlers.registration import register_exception_handlers
from app.core.handlers.validation import validation_exception_handler

__all__ = [
    "domain_exception_handler",
    "http_exception_handler",
    "register_exception_handlers",
    "validation_exception_handler",
]
