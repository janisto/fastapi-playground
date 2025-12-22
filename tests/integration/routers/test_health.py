"""
Integration tests for health endpoint.
"""

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """
    Tests for GET /health/.
    """

    def test_returns_200(self, client: TestClient) -> None:
        """
        Verify health endpoint returns 200 OK.
        """
        response = client.get("/health/")

        assert response.status_code == 200

    def test_returns_healthy_status(self, client: TestClient) -> None:
        """
        Verify health endpoint returns healthy status.
        """
        response = client.get("/health/")

        body = response.json()
        assert body["status"] == "healthy"

    def test_returns_json_content_type(self, client: TestClient) -> None:
        """
        Verify health endpoint returns JSON content type.
        """
        response = client.get("/health/")

        assert response.headers.get("content-type") == "application/json"

    def test_no_auth_required(self, client: TestClient) -> None:
        """
        Verify health endpoint does not require authentication.
        """
        response = client.get("/health/")

        assert response.status_code == 200
