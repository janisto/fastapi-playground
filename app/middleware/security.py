"""
Security-related middleware and utilities.

Headers follow OWASP REST Security Cheat Sheet recommendations.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings

# Permissions-Policy disables browser features not needed by REST APIs
_DEFAULT_PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Attach security headers to all responses per OWASP REST Security guidelines.

    Headers set:
      - Cache-Control: no-store - Prevents caching of API responses
      - Content-Security-Policy: frame-ancestors 'none' - Prevents framing (CSP Level 2)
      - Cross-Origin-Opener-Policy: same-origin - Isolates browsing context (Spectre mitigation)
      - Cross-Origin-Resource-Policy: same-origin - Prevents cross-origin reads (Spectre mitigation)
      - Permissions-Policy: disables browser features not needed by REST APIs
      - Referrer-Policy: strict-origin-when-cross-origin - Controls referrer information leakage
      - Strict-Transport-Security (when HTTPS) - Enforces HTTPS connections
      - X-Content-Type-Options: nosniff - Prevents MIME-sniffing attacks
      - X-Frame-Options: DENY - Prevents clickjacking (legacy browser support)
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        hsts: bool = True,
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        x_frame_options: str = "DENY",
        referrer_policy: str = "strict-origin-when-cross-origin",
        cache_control: str = "no-store",
        content_security_policy: str = "frame-ancestors 'none'",
        cross_origin_opener_policy: str = "same-origin",
        cross_origin_resource_policy: str = "same-origin",
        permissions_policy: str = _DEFAULT_PERMISSIONS_POLICY,
    ) -> None:
        super().__init__(app)
        self._settings = get_settings()
        self._hsts = hsts
        self._hsts_include_subdomains = hsts_include_subdomains
        self._hsts_preload = hsts_preload
        self._x_frame_options = x_frame_options
        self._referrer_policy = referrer_policy
        self._cache_control = cache_control
        self._content_security_policy = content_security_policy
        self._cross_origin_opener_policy = cross_origin_opener_policy
        self._cross_origin_resource_policy = cross_origin_resource_policy
        self._permissions_policy = permissions_policy

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Vary: Origin, Accept - important for proper caching (RFC 9110 Section 12.5.5)
        # - Origin: CORS responses vary by requesting origin
        # - Accept: Content negotiation (JSON vs CBOR) varies by Accept header
        response.headers.setdefault("Vary", "Origin, Accept")

        # Cache-Control (OWASP recommends no-store for API responses)
        if self._cache_control:
            response.headers.setdefault("Cache-Control", self._cache_control)

        # Content-Security-Policy (defense-in-depth for JSON APIs)
        # Skip strict CSP for documentation endpoints that need external scripts
        is_docs_path = request.url.path in ("/api-docs", "/api-redoc", "/openapi.json")
        if self._content_security_policy and not is_docs_path:
            response.headers.setdefault("Content-Security-Policy", self._content_security_policy)

        # Cross-Origin-Opener-Policy (Spectre mitigation)
        if self._cross_origin_opener_policy:
            response.headers.setdefault("Cross-Origin-Opener-Policy", self._cross_origin_opener_policy)

        # Cross-Origin-Resource-Policy (Spectre mitigation)
        if self._cross_origin_resource_policy:
            response.headers.setdefault("Cross-Origin-Resource-Policy", self._cross_origin_resource_policy)

        # Permissions-Policy (disable browser features not needed by REST APIs)
        if self._permissions_policy:
            response.headers.setdefault("Permissions-Policy", self._permissions_policy)

        # Referrer-Policy
        if self._referrer_policy:
            response.headers.setdefault("Referrer-Policy", self._referrer_policy)

        # X-Content-Type-Options
        response.headers.setdefault("X-Content-Type-Options", "nosniff")

        # X-Frame-Options (legacy browser support)
        if self._x_frame_options:
            response.headers.setdefault("X-Frame-Options", self._x_frame_options)

        # HSTS only on HTTPS and typically not in debug
        if self._hsts and (request.url.scheme == "https") and not self._settings.debug:
            parts = ["max-age=31536000"]
            if self._hsts_include_subdomains:
                parts.append("includeSubDomains")
            if self._hsts_preload:
                parts.append("preload")
            response.headers.setdefault("Strict-Transport-Security", "; ".join(parts))

        return response
