"""
Security-related middleware and utilities.

Headers follow OWASP REST Security Cheat Sheet recommendations.
"""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings

# Permissions-Policy disables browser features not needed by REST APIs
_DEFAULT_PERMISSIONS_POLICY = (
    "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
)


class SecurityHeadersMiddleware:
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
        self.app = app
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

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                self._apply_headers(MutableHeaders(scope=message), scope)
            await send(message)

        await self.app(scope, receive, send_with_security_headers)

    def _apply_headers(self, headers: MutableHeaders, scope: Scope) -> None:
        headers.add_vary_header("Accept")

        if self._cache_control:
            headers.setdefault("Cache-Control", self._cache_control)

        path = str(scope.get("path", ""))
        is_docs_path = path in ("/api-docs", "/api-redoc", "/openapi.json")
        if self._content_security_policy and not is_docs_path:
            headers.setdefault("Content-Security-Policy", self._content_security_policy)

        optional_headers = {
            "Cross-Origin-Opener-Policy": self._cross_origin_opener_policy,
            "Cross-Origin-Resource-Policy": self._cross_origin_resource_policy,
            "Permissions-Policy": self._permissions_policy,
            "Referrer-Policy": self._referrer_policy,
            "X-Frame-Options": self._x_frame_options,
        }
        for name, value in optional_headers.items():
            if value:
                headers.setdefault(name, value)

        headers.setdefault("X-Content-Type-Options", "nosniff")

        if self._hsts and scope.get("scheme") == "https" and not self._settings.debug:
            parts = ["max-age=31536000"]
            if self._hsts_include_subdomains:
                parts.append("includeSubDomains")
            if self._hsts_preload:
                parts.append("preload")
            headers.setdefault("Strict-Transport-Security", "; ".join(parts))
