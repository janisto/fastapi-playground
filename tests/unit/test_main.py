"""
Unit tests for application lifespan and main module.
"""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_request_observability import (
    AccessLogMiddleware,
    LoggingPreset,
    RequestContextMiddleware,
    TraceContextLevel,
)

from app.middleware import SecurityHeadersMiddleware


def _build_cors_test_app() -> RequestContextMiddleware:
    from app.core.config import Settings
    from app.main import _build_application

    return _build_application(
        FastAPI(),
        Settings(
            firebase_project_id="test-project",
            environment="test",
            cors_origins=["http://localhost:3000"],
        ),
    )


class TestLifespan:
    """
    Tests for application lifespan events.
    """

    def test_startup_initializes_logging(self) -> None:
        """
        Verify lifespan startup configures logging.
        """
        with (
            patch("app.main.configure_logging") as mock_configure_logging,
            patch("app.main.close_async_firestore_client"),
        ):
            from app.main import app

            with TestClient(app):
                mock_configure_logging.assert_called_once()

    def test_startup_does_not_initialize_firebase(self) -> None:
        """
        Verify public application startup remains independent of Firebase.
        """
        with (
            patch("app.main.configure_logging"),
            patch("app.core.firebase.initialize_firebase") as mock_init_firebase,
            patch("app.main.close_async_firestore_client"),
        ):
            from app.main import app

            with TestClient(app):
                mock_init_firebase.assert_not_called()

    def test_shutdown_closes_firestore_client(self) -> None:
        """
        Verify lifespan shutdown calls close_async_firestore_client.
        """
        with (
            patch("app.main.configure_logging"),
            patch("app.main.close_async_firestore_client") as mock_close,
        ):
            from app.main import app

            with TestClient(app):
                pass

            mock_close.assert_called_once_with()


class TestAppConfiguration:
    """
    Tests for FastAPI app configuration.
    """

    def test_app_title(self) -> None:
        """
        Verify app has correct title.
        """
        from app.main import fastapi_app

        assert fastapi_app.title == "FastAPI Playground"

    def test_app_version(self) -> None:
        """
        Verify app has correct version.
        """
        from app.main import fastapi_app

        assert fastapi_app.version == "0.1.0"

    def test_docs_url(self) -> None:
        """
        Verify API docs URL is configured.
        """
        from app.main import fastapi_app

        assert fastapi_app.docs_url == "/api-docs"

    def test_redoc_url(self) -> None:
        """
        Verify ReDoc URL is configured.
        """
        from app.main import fastapi_app

        assert fastapi_app.redoc_url == "/api-redoc"

    def test_optional_documentation_uis_render_the_runtime_document(self) -> None:
        from app.main import app

        with TestClient(app) as client:
            for path in ("/api-docs", "/api-redoc"):
                response = client.get(path)
                assert response.status_code == 200
                assert response.headers["Content-Type"].startswith("text/html")
                assert "/openapi.json" in response.text

    def test_observability_middleware_configuration(self) -> None:
        """
        Verify request context wraps GCP access logging.
        """
        from app.main import access_log_middleware, app, security_headers_middleware, settings

        assert isinstance(app, RequestContextMiddleware)
        assert isinstance(security_headers_middleware, SecurityHeadersMiddleware)
        assert isinstance(access_log_middleware, AccessLogMiddleware)
        access_config = access_log_middleware.config
        assert access_config.preset is LoggingPreset.GCP
        assert access_config.logger.name == "http.access"
        assert access_config.trace_context_level is TraceContextLevel.LEVEL_1
        assert app.config.trace_context_level is access_config.trace_context_level
        assert access_config.capture_path is False
        assert access_config.capture_peer_ip is False
        assert access_config.capture_user_agent is False
        assert access_config.capture_error is False
        assert security_headers_middleware._hsts is settings.is_production


class TestRouterConfiguration:
    """
    Tests for router registration.
    """

    def test_profile_router_included(self) -> None:
        """
        Verify profile router is included.
        """
        from app.main import fastapi_app

        assert "/v1/profile" in fastapi_app.openapi()["paths"]

    def test_health_router_included(self) -> None:
        """
        Verify health router is included.
        """
        from app.main import fastapi_app

        assert "/health" in fastapi_app.openapi()["paths"]


class TestCORSMiddleware:
    """
    Tests for CORS middleware configuration.
    """

    def test_cors_preflight_handled_when_configured(self) -> None:
        """
        Verify CORS preflight requests work when origins are configured.
        """
        with TestClient(_build_cors_test_app()) as client:
            response = client.options(
                "/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_error_response_has_one_origin_variance(self) -> None:
        """
        Verify the outer CORS middleware is the single owner of CORS headers.
        """
        with TestClient(_build_cors_test_app(), raise_server_exceptions=False) as client:
            response = client.get("/missing", headers={"Origin": "http://localhost:3000"})

        assert response.status_code == 404
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert response.headers["vary"].split(", ").count("Origin") == 1

    def test_cors_allows_specific_methods(self) -> None:
        """
        Verify CORS is configured with specific allowed methods, not wildcards.
        """
        with TestClient(_build_cors_test_app()) as client:
            response = client.options(
                "/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                },
            )

        allowed_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods
        assert "PATCH" in allowed_methods
        assert "DELETE" in allowed_methods
        assert "PUT" not in allowed_methods

    def test_cors_allows_specific_headers(self) -> None:
        """
        Verify CORS is configured with specific allowed headers, not wildcards.
        """
        with TestClient(_build_cors_test_app()) as client:
            response = client.options(
                "/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization, Content-Type",
                },
            )

        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "authorization" in allowed_headers
        assert "content-type" in allowed_headers

    def test_cors_allows_trace_context_headers_for_logging(self) -> None:
        """
        Verify CORS allows W3C trace context headers for observability middleware.
        """
        with TestClient(_build_cors_test_app()) as client:
            response = client.options(
                "/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "traceparent, tracestate",
                },
            )

        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "traceparent" in allowed_headers
        assert "tracestate" in allowed_headers

    def test_cors_exposes_portable_response_metadata(self) -> None:
        with TestClient(_build_cors_test_app()) as client:
            response = client.get("/", headers={"Origin": "http://localhost:3000"})

        exposed = {name.strip().lower() for name in response.headers["access-control-expose-headers"].split(",")}
        assert exposed == {"link", "location", "retry-after", "x-ratelimit-reset", "x-request-id"}
