"""
Unit tests for security headers middleware.
"""

from unittest.mock import patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient

from app.middleware.security import SecurityHeadersMiddleware
from tests.helpers.starlette_utils import build_starlette_app


def _create_app(
    hsts: bool = True,
    x_frame_options: str = "DENY",
    referrer_policy: str = "strict-origin-when-cross-origin",
) -> Starlette:
    """
    Create a minimal Starlette app with security middleware.
    """

    async def ping(request: Request) -> PlainTextResponse:
        return PlainTextResponse("pong")

    return build_starlette_app(
        routes=[("/ping", ping, ["GET"])],
        middleware=[
            (
                SecurityHeadersMiddleware,
                {
                    "hsts": hsts,
                    "x_frame_options": x_frame_options,
                    "referrer_policy": referrer_policy,
                },
            )
        ],
    )


class TestSecurityHeaders:
    """
    Tests for SecurityHeadersMiddleware.
    """

    def test_x_frame_options_deny(self) -> None:
        """
        Verify X-Frame-Options header is set to DENY.
        """
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert response.status_code == 200
            assert response.headers.get("x-frame-options") == "DENY"

    def test_x_content_type_options_nosniff(self) -> None:
        """
        Verify X-Content-Type-Options header is set to nosniff.
        """
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert response.headers.get("x-content-type-options") == "nosniff"

    def test_referrer_policy_strict_origin_when_cross_origin(self) -> None:
        """
        Verify Referrer-Policy header is set to strict-origin-when-cross-origin.
        """
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_custom_x_frame_options(self) -> None:
        """
        Verify custom X-Frame-Options value is applied.
        """
        with TestClient(_create_app(x_frame_options="SAMEORIGIN")) as client:
            response = client.get("/ping")
            assert response.headers.get("x-frame-options") == "SAMEORIGIN"

    def test_custom_referrer_policy(self) -> None:
        """
        Verify custom Referrer-Policy value is applied.
        """
        with TestClient(_create_app(referrer_policy="strict-origin")) as client:
            response = client.get("/ping")
            assert response.headers.get("referrer-policy") == "strict-origin"

    def test_no_hsts_on_http(self) -> None:
        """
        Verify HSTS header is not set for HTTP requests.
        """
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert "strict-transport-security" not in response.headers


class TestHSTSDefaultSettings:
    """
    Tests for HSTS with default production settings.

    These tests verify that HSTS is correctly applied when using default
    configuration (debug=False), ensuring production deployments are secure.
    """

    def test_hsts_enabled_with_default_settings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify HSTS is applied on HTTPS with default settings (debug=False).

        This test ensures the security fix for debug defaulting to False is
        working correctly and HSTS will be applied in production.
        """
        from app.core.config import Settings

        monkeypatch.delenv("DEBUG", raising=False)

        settings = Settings(_env_file=None)
        assert settings.debug is False, "debug must default to False for production safety"

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"hsts": True, "hsts_include_subdomains": True})],
        )

        with (
            patch("app.middleware.security.get_settings", return_value=settings),
            TestClient(app, base_url="https://testserver") as client,
        ):
            response = client.get("/ping")
            hsts = response.headers.get("strict-transport-security")
            assert hsts is not None, "HSTS must be set with default production settings"
            assert "max-age=31536000" in hsts
            assert "includeSubDomains" in hsts


class TestHSTSHeader:
    """
    Tests for HSTS header behavior.
    """

    def test_hsts_on_https_in_production(self) -> None:
        """
        Verify HSTS header is set for HTTPS in production mode (debug=False).

        This is critical for security - HSTS must be applied in production
        to prevent HTTPS downgrade attacks.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[
                (
                    SecurityHeadersMiddleware,
                    {"hsts": True, "hsts_include_subdomains": True, "hsts_preload": False},
                )
            ],
        )

        # Patch settings to non-debug mode
        with patch("app.middleware.security.get_settings") as mock_settings:
            mock_settings.return_value.debug = False
            with TestClient(app, base_url="https://testserver") as client:
                response = client.get("/ping")
                hsts = response.headers.get("strict-transport-security")
                assert hsts is not None, "HSTS header must be set for HTTPS in production"
                assert "max-age=31536000" in hsts
                assert "includeSubDomains" in hsts

    def test_no_hsts_in_debug_mode(self) -> None:
        """
        Verify HSTS header is not set in debug mode.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"hsts": True})],
        )

        with patch("app.middleware.security.get_settings") as mock_settings:
            mock_settings.return_value.debug = True
            with TestClient(app, base_url="https://testserver") as client:
                response = client.get("/ping")
                assert "strict-transport-security" not in response.headers

    def test_hsts_without_include_subdomains(self) -> None:
        """
        Verify HSTS header omits includeSubDomains when disabled.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[
                (
                    SecurityHeadersMiddleware,
                    {"hsts": True, "hsts_include_subdomains": False, "hsts_preload": False},
                )
            ],
        )

        with patch("app.middleware.security.get_settings") as mock_settings:
            mock_settings.return_value.debug = False
            with TestClient(app, base_url="https://testserver") as client:
                response = client.get("/ping")
                hsts = response.headers.get("strict-transport-security")
                assert hsts is not None
                assert hsts == "max-age=31536000"
                assert "includeSubDomains" not in hsts

    def test_hsts_with_preload(self) -> None:
        """
        Verify HSTS header includes preload directive when enabled.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[
                (
                    SecurityHeadersMiddleware,
                    {"hsts": True, "hsts_include_subdomains": True, "hsts_preload": True},
                )
            ],
        )

        with patch("app.middleware.security.get_settings") as mock_settings:
            mock_settings.return_value.debug = False
            with TestClient(app, base_url="https://testserver") as client:
                response = client.get("/ping")
                hsts = response.headers.get("strict-transport-security")
                assert hsts is not None
                assert "max-age=31536000" in hsts
                assert "includeSubDomains" in hsts
                assert "preload" in hsts


class TestCrossOriginOpenerPolicyHeader:
    """
    Tests for Cross-Origin-Opener-Policy header.

    COOP isolates the browsing context to exclusively same-origin documents,
    protecting against Spectre-style side-channel attacks.
    """

    def test_coop_same_origin_by_default(self) -> None:
        """
        Verify Cross-Origin-Opener-Policy header is set to same-origin by default.
        """
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert response.headers.get("cross-origin-opener-policy") == "same-origin"

    def test_custom_coop(self) -> None:
        """
        Verify custom Cross-Origin-Opener-Policy value can be configured.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"cross_origin_opener_policy": "same-origin-allow-popups"})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert response.headers.get("cross-origin-opener-policy") == "same-origin-allow-popups"

    def test_empty_coop_not_set(self) -> None:
        """
        Verify empty Cross-Origin-Opener-Policy config omits the header.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"cross_origin_opener_policy": ""})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert "cross-origin-opener-policy" not in response.headers


class TestCrossOriginResourcePolicyHeader:
    """
    Tests for Cross-Origin-Resource-Policy header.

    CORP prevents cross-origin reads of resources, providing defense
    against Spectre-style side-channel attacks.
    """

    def test_corp_same_origin_by_default(self) -> None:
        """
        Verify Cross-Origin-Resource-Policy header is set to same-origin by default.
        """
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert response.headers.get("cross-origin-resource-policy") == "same-origin"

    def test_custom_corp(self) -> None:
        """
        Verify custom Cross-Origin-Resource-Policy value can be configured.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"cross_origin_resource_policy": "same-site"})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert response.headers.get("cross-origin-resource-policy") == "same-site"

    def test_empty_corp_not_set(self) -> None:
        """
        Verify empty Cross-Origin-Resource-Policy config omits the header.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"cross_origin_resource_policy": ""})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert "cross-origin-resource-policy" not in response.headers


class TestPermissionsPolicyHeader:
    """
    Tests for Permissions-Policy header.

    Permissions-Policy (formerly Feature-Policy) disables browser features
    not needed by REST APIs, reducing the attack surface.
    """

    def test_permissions_policy_set_by_default(self) -> None:
        """
        Verify Permissions-Policy header is set with disabled features by default.
        """
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            policy = response.headers.get("permissions-policy")
            assert policy is not None
            assert "accelerometer=()" in policy
            assert "camera=()" in policy
            assert "geolocation=()" in policy
            assert "microphone=()" in policy
            assert "payment=()" in policy

    def test_custom_permissions_policy(self) -> None:
        """
        Verify custom Permissions-Policy value can be configured.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"permissions_policy": "geolocation=(), camera=()"})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert response.headers.get("permissions-policy") == "geolocation=(), camera=()"

    def test_empty_permissions_policy_not_set(self) -> None:
        """
        Verify empty Permissions-Policy config omits the header.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"permissions_policy": ""})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert "permissions-policy" not in response.headers


class TestSecurityHeadersDisabled:
    """
    Tests for disabled security headers.
    """

    def test_empty_x_frame_options_not_set(self) -> None:
        """
        Verify empty X-Frame-Options config omits the header.
        """
        with TestClient(_create_app(x_frame_options="")) as client:
            response = client.get("/ping")
            assert "x-frame-options" not in response.headers

    def test_empty_referrer_policy_not_set(self) -> None:
        """
        Verify empty Referrer-Policy config omits the header.
        """
        with TestClient(_create_app(referrer_policy="")) as client:
            response = client.get("/ping")
            assert "referrer-policy" not in response.headers


class TestCacheControlHeader:
    """
    Tests for Cache-Control header.

    OWASP recommends Cache-Control: no-store for API responses
    to prevent caching of sensitive data by proxies or browsers.
    """

    def test_cache_control_no_store_by_default(self) -> None:
        """
        Verify Cache-Control header is set to no-store by default.
        """
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert response.headers.get("cache-control") == "no-store"

    def test_custom_cache_control(self) -> None:
        """
        Verify custom Cache-Control value can be configured.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"cache_control": "no-cache, no-store, must-revalidate"})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert response.headers.get("cache-control") == "no-cache, no-store, must-revalidate"

    def test_empty_cache_control_not_set(self) -> None:
        """
        Verify empty Cache-Control config omits the header.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"cache_control": ""})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert "cache-control" not in response.headers


class TestContentSecurityPolicyHeader:
    """
    Tests for Content-Security-Policy header.

    OWASP recommends CSP for defense-in-depth. For JSON APIs,
    `default-src 'none'` prevents any resource loading if responses
    are accidentally rendered as HTML.
    """

    def test_csp_frame_ancestors_none_by_default(self) -> None:
        """
        Verify Content-Security-Policy header is set to frame-ancestors 'none' by default.

        Per OWASP REST API Security Cheat Sheet, frame-ancestors 'none' is recommended
        for REST APIs to prevent clickjacking without being overly restrictive.
        """
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert response.headers.get("content-security-policy") == "frame-ancestors 'none'"

    def test_custom_csp(self) -> None:
        """
        Verify custom Content-Security-Policy value can be configured.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"content_security_policy": "default-src 'self'"})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert response.headers.get("content-security-policy") == "default-src 'self'"

    def test_empty_csp_not_set(self) -> None:
        """
        Verify empty Content-Security-Policy config omits the header.
        """

        async def ping(request: Request) -> PlainTextResponse:
            return PlainTextResponse("pong")

        app = build_starlette_app(
            routes=[("/ping", ping, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {"content_security_policy": ""})],
        )

        with TestClient(app) as client:
            response = client.get("/ping")
            assert "content-security-policy" not in response.headers


class TestCSPDocumentationExemption:
    """
    Tests for CSP exemption on API documentation paths.

    Documentation endpoints (/api-docs, /api-redoc, /openapi.json) need to load
    external JavaScript from CDNs (Swagger UI, ReDoc). The strict CSP policy
    must be skipped for these paths to allow the documentation to render.
    """

    @pytest.mark.parametrize(
        "path",
        ["/api-docs", "/api-redoc", "/openapi.json"],
        ids=["swagger-ui", "redoc", "openapi-json"],
    )
    def test_csp_skipped_for_documentation_paths(self, path: str) -> None:
        """
        Verify Content-Security-Policy header is not set for documentation paths.
        """

        async def docs_handler(request: Request) -> PlainTextResponse:
            return PlainTextResponse("docs content")

        app = build_starlette_app(
            routes=[(path, docs_handler, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {})],
        )

        with TestClient(app) as client:
            response = client.get(path)
            assert response.status_code == 200
            assert "content-security-policy" not in response.headers

    def test_csp_applied_for_non_documentation_paths(self) -> None:
        """
        Verify Content-Security-Policy header is still set for regular API paths.
        """

        async def api_handler(request: Request) -> PlainTextResponse:
            return PlainTextResponse("api response")

        app = build_starlette_app(
            routes=[("/api/users", api_handler, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {})],
        )

        with TestClient(app) as client:
            response = client.get("/api/users")
            assert response.status_code == 200
            assert response.headers.get("content-security-policy") == "frame-ancestors 'none'"

    def test_other_security_headers_still_applied_for_documentation_paths(self) -> None:
        """
        Verify other security headers are still applied even when CSP is skipped.

        Documentation paths should only skip CSP, not other security headers.
        """

        async def docs_handler(request: Request) -> PlainTextResponse:
            return PlainTextResponse("docs content")

        app = build_starlette_app(
            routes=[("/api-docs", docs_handler, ["GET"])],
            middleware=[(SecurityHeadersMiddleware, {})],
        )

        with TestClient(app) as client:
            response = client.get("/api-docs")
            assert response.status_code == 200
            # CSP should be skipped
            assert "content-security-policy" not in response.headers
            # But other security headers should still be present
            assert response.headers.get("x-content-type-options") == "nosniff"
            assert response.headers.get("x-frame-options") == "DENY"
            assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
            assert response.headers.get("cache-control") == "no-store"
