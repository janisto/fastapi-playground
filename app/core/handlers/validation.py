"""
Request validation exception handler.
"""

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle request validation errors.
    """
    logger.warning("Validation error", extra={"errors": exc.errors(), "path": request.url.path})
    return JSONResponse(status_code=422, content={"detail": exc.errors()})
