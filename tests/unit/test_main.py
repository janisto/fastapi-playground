"""
Unit tests for application lifespan and main module.
"""

import sys
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestLifespan:
    """
    Tests for application lifespan events.
    """

    def test_startup_initializes_logging(self) -> None:
        """
        Verify lifespan startup calls setup_logging.
        """
        with (
            patch("app.main.setup_logging") as mock_setup_logging,
            patch("app.main.initialize_firebase"),
            patch("app.main.close_async_firestore_client", new_callable=AsyncMock),
        ):
            from app.main import app

            with TestClient(app):
                mock_setup_logging.assert_called_once()

    def test_startup_initializes_firebase(self) -> None:
        """
        Verify lifespan startup calls initialize_firebase.
        """
        with (
            patch("app.main.setup_logging"),
            patch("app.main.initialize_firebase") as mock_init_firebase,
            patch("app.main.close_async_firestore_client", new_callable=AsyncMock),
        ):
            from app.main import app

            with TestClient(app):
                mock_init_firebase.assert_called_once()

    def test_shutdown_closes_firestore_client(self) -> None:
        """
        Verify lifespan shutdown calls close_async_firestore_client.
        """
        with (
            patch("app.main.setup_logging"),
            patch("app.main.initialize_firebase"),
            patch("app.main.close_async_firestore_client", new_callable=AsyncMock) as mock_close,
        ):
            from app.main import app

            with TestClient(app):
                pass

            mock_close.assert_awaited_once()


class TestAppConfiguration:
    """
    Tests for FastAPI app configuration.
    """

    def test_app_title(self) -> None:
        """
        Verify app has correct title.
        """
        from app.main import app

        assert app.title == "FastAPI Playground"

    def test_app_version(self) -> None:
        """
        Verify app has correct version.
        """
        from app.main import app

        assert app.version == "0.1.0"

    def test_docs_url(self) -> None:
        """
        Verify API docs URL is configured.
        """
        from app.main import app

        assert app.docs_url == "/api-docs"

    def test_redoc_url(self) -> None:
        """
        Verify ReDoc URL is configured.
        """
        from app.main import app

        assert app.redoc_url == "/api-redoc"


class TestRouterConfiguration:
    """
    Tests for router registration.
    """

    def test_profile_router_included(self) -> None:
        """
        Verify profile router is included.
        """
        from app.main import app

        routes = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/v1/profile" in routes

    def test_health_router_included(self) -> None:
        """
        Verify health router is included.
        """
        from app.main import app

        routes = [route.path for route in app.routes if hasattr(route, "path")]
        assert "/health" in routes


class TestCorsMiddleware:
    """
    Tests for CORS middleware configuration.
    """

    def test_cors_middleware_added_when_origins_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Verify CORS middleware is added when cors_origins is not empty.
        """
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')

        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        if "app.core.config" in sys.modules:
            del sys.modules["app.core.config"]

        with (
            patch("app.main.setup_logging"),
            patch("app.main.initialize_firebase"),
            patch("app.main.close_async_firestore_client", new_callable=AsyncMock),
        ):
            from app.main import app

            middleware_classes = [m.cls.__name__ for m in app.user_middleware if hasattr(m.cls, "__name__")]
            assert "CORSMiddleware" in middleware_classes

    def test_cors_preflight_handled_when_configured(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Verify CORS preflight requests work when origins are configured.
        """
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')

        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        if "app.core.config" in sys.modules:
            del sys.modules["app.core.config"]

        with (
            patch("app.main.setup_logging"),
            patch("app.main.initialize_firebase"),
            patch("app.main.close_async_firestore_client", new_callable=AsyncMock),
        ):
            from app.main import app

            with TestClient(app) as client:
                response = client.options(
                    "/",
                    headers={
                        "Origin": "http://localhost:3000",
                        "Access-Control-Request-Method": "GET",
                    },
                )

            assert response.status_code == 200
            assert "access-control-allow-origin" in response.headers

    def test_cors_allows_specific_methods(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Verify CORS is configured with specific allowed methods, not wildcards.
        """
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')

        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        if "app.core.config" in sys.modules:
            del sys.modules["app.core.config"]

        with (
            patch("app.main.setup_logging"),
            patch("app.main.initialize_firebase"),
            patch("app.main.close_async_firestore_client", new_callable=AsyncMock),
        ):
            from app.main import app

            with TestClient(app) as client:
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
            assert "PUT" in allowed_methods
            assert "PATCH" in allowed_methods
            assert "DELETE" in allowed_methods
            assert "OPTIONS" in allowed_methods

    def test_cors_allows_specific_headers(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Verify CORS is configured with specific allowed headers, not wildcards.
        """
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')

        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        if "app.core.config" in sys.modules:
            del sys.modules["app.core.config"]

        with (
            patch("app.main.setup_logging"),
            patch("app.main.initialize_firebase"),
            patch("app.main.close_async_firestore_client", new_callable=AsyncMock),
        ):
            from app.main import app

            with TestClient(app) as client:
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

    def test_cors_allows_traceparent_header_for_logging(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        Verify CORS allows traceparent header for logging middleware.
        """
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000"]')

        if "app.main" in sys.modules:
            del sys.modules["app.main"]
        if "app.core.config" in sys.modules:
            del sys.modules["app.core.config"]

        with (
            patch("app.main.setup_logging"),
            patch("app.main.initialize_firebase"),
            patch("app.main.close_async_firestore_client", new_callable=AsyncMock),
        ):
            from app.main import app

            with TestClient(app) as client:
                response = client.options(
                    "/",
                    headers={
                        "Origin": "http://localhost:3000",
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "traceparent",
                    },
                )

            allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
            assert "traceparent" in allowed_headers
