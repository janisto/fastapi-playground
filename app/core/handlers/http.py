"""
HTTP exception handler.
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handle HTTP exceptions with appropriate logging.
    """
    extra = {"status_code": exc.status_code, "detail": exc.detail, "path": request.url.path}
    if exc.status_code >= 500:
        logger.error("HTTP error", extra=extra)
    else:
        logger.warning("Client error", extra=extra)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
