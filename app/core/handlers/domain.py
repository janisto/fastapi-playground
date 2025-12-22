"""
Domain exception handler.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import DomainError


async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    """
    Handle all domain exceptions generically.
    """
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
