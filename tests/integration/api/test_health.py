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
        response = client.get("/health")

        assert response.status_code == 200

    def test_returns_healthy_status(self, client: TestClient) -> None:
        """
        Verify health endpoint returns healthy status.
        """
        response = client.get("/health")

        body = response.json()
        assert body["status"] == "healthy"

    def test_returns_schema_url(self, client: TestClient) -> None:
        """
        Verify health endpoint returns $schema URL.
        """
        response = client.get("/health")

        body = response.json()
        assert "$schema" in body
        assert "schemas/HealthResponse.json" in body["$schema"]

    def test_returns_describedby_link_header(self, client: TestClient) -> None:
        """
        Verify health endpoint returns Link header with describedBy.
        """
        response = client.get("/health")

        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link
        assert "/schemas/HealthResponse.json" in link

    def test_returns_json_content_type(self, client: TestClient) -> None:
        """
        Verify health endpoint returns JSON content type.
        """
        response = client.get("/health")

        assert response.headers.get("content-type") == "application/json"

    def test_no_auth_required(self, client: TestClient) -> None:
        """
        Verify health endpoint does not require authentication.
        """
        response = client.get("/health")

        assert response.status_code == 200
