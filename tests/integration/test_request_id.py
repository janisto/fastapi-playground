"""
Integration tests for X-Request-ID header propagation.
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.exceptions import ProfileNotFoundError
from tests.helpers.profiles import make_profile


class TestRequestIdPropagation:
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

        response = client.get("/profile/")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36
        assert request_id.count("-") == 4

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
            "/profile/",
            headers={"X-Request-ID": "my-custom-request-id"},
        )

        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == "my-custom-request-id"


class TestRequestIdInErrorResponses:
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

        response = client.get("/profile/")

        assert response.status_code == 404
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36

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
            "/profile/",
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
            "/profile/",
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
            "/profile/",
            headers={"X-Request-ID": "unauthorized-test-id"},
        )

        assert response.status_code == 401
        assert response.headers["X-Request-ID"] == "unauthorized-test-id"
