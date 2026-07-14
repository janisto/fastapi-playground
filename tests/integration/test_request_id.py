"""
Integration tests for X-Request-ID header propagation.
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.auth.firebase import verify_firebase_token
from app.exceptions import ProfileNotFoundError
from tests.helpers.profiles import make_profile


class TestRequestIDPropagation:
    """
    Tests for X-Request-ID header in success responses.
    """

    def test_returns_request_id_header_on_success(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify X-Request-ID is returned in successful response.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get("/v1/profile")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 32
        assert bytes.fromhex(request_id)

    def test_echoes_incoming_request_id(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify incoming X-Request-ID is echoed back.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(
            "/v1/profile",
            headers={"X-Request-ID": "my-custom-request-id"},
        )

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == "my-custom-request-id"

    def test_replaces_invalid_incoming_request_id(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify invalid request IDs are replaced with a safe generated value.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(
            "/v1/profile",
            headers={"X-Request-ID": "invalid request id"},
        )

        assert response.status_code == 200
        request_id = response.headers["X-Request-ID"]
        assert request_id != "invalid request id"
        assert len(request_id) == 32
        assert bytes.fromhex(request_id)


class TestRequestIDInErrorResponses:
    """
    Tests for X-Request-ID header in error responses.
    """

    def test_returns_request_id_on_404_error(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify X-Request-ID is returned in 404 error response.
        """
        mock_profile_service.get_profile.side_effect = ProfileNotFoundError()

        response = client.get("/v1/profile")

        assert response.status_code == 404
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 32
        assert bytes.fromhex(request_id)

    def test_echoes_request_id_on_error(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify incoming X-Request-ID is echoed back in error response.
        """
        mock_profile_service.get_profile.side_effect = ProfileNotFoundError()

        response = client.get(
            "/v1/profile",
            headers={"X-Request-ID": "error-test-request-id"},
        )

        assert response.status_code == 404
        assert response.headers["X-Request-ID"] == "error-test-request-id"

    def test_returns_request_id_on_validation_error(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify X-Request-ID is returned in 422 validation error response.
        """
        response = client.post(
            "/v1/profile",
            json={},
            headers={"X-Request-ID": "validation-error-test-id"},
        )

        assert response.status_code == 422
        assert response.headers["X-Request-ID"] == "validation-error-test-id"

    def test_returns_request_id_on_401_unauthorized(
        self,
        client: TestClient,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify X-Request-ID is returned in 401 unauthorized response.
        """
        response = client.get(
            "/v1/profile",
            headers={"X-Request-ID": "unauthorized-test-id"},
        )

        assert response.status_code == 401
        assert response.headers["X-Request-ID"] == "unauthorized-test-id"

    def test_returns_request_id_on_500_error(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify handled server errors retain the package request ID.
        """
        mock_profile_service.get_profile.side_effect = RuntimeError("database unavailable")

        response = client.get(
            "/v1/profile",
            headers={"X-Request-ID": "server-error-test-id"},
        )

        assert response.status_code == 500
        assert response.headers["X-Request-ID"] == "server-error-test-id"

    def test_returns_request_id_and_security_headers_on_unhandled_500(
        self,
        client: TestClient,
    ) -> None:
        """
        Verify outer ASGI middleware observes FastAPI's final recovery response.
        """

        def fail_authentication() -> None:
            raise RuntimeError("dependency failed")

        from app.main import fastapi_app

        fastapi_app.dependency_overrides[verify_firebase_token] = fail_authentication
        try:
            response = client.get(
                "/v1/profile",
                headers={"X-Request-ID": "unhandled-error-test-id"},
            )
        finally:
            fastapi_app.dependency_overrides.pop(verify_firebase_token, None)

        assert response.status_code == 500
        assert response.headers["X-Request-ID"] == "unhandled-error-test-id"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
