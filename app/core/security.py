"""Security-related middleware and utilities."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach common security headers to all responses.

    Adds:
      - Strict-Transport-Security (when HTTPS)
      - X-Content-Type-Options: nosniff
      - X-Frame-Options: DENY
      - Referrer-Policy: same-origin
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        hsts: bool = True,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        x_frame_options: str = "DENY",
        referrer_policy: str = "same-origin",
    ) -> None:
        super().__init__(app)
        self._settings = get_settings()
        self._hsts = hsts
        self._hsts_include_subdomains = hsts_include_subdomains
        self._hsts_preload = hsts_preload
        self._x_frame_options = x_frame_options
        self._referrer_policy = referrer_policy

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # X-Content-Type-Options
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # X-Frame-Options
        if self._x_frame_options:
            response.headers.setdefault("X-Frame-Options", self._x_frame_options)

        # Referrer-Policy
        if self._referrer_policy:
            response.headers.setdefault("Referrer-Policy", self._referrer_policy)

        # HSTS only on HTTPS and typically not in debug
        if self._hsts and (request.url.scheme == "https") and not self._settings.debug:
            parts = ["max-age=31536000"]
            if self._hsts_include_subdomains:
                parts.append("includeSubDomains")
            if self._hsts_preload:
                parts.append("preload")
            response.headers.setdefault("Strict-Transport-Security", "; ".join(parts))

        return response
