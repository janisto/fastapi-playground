"""
Integration tests for root endpoint.
"""

from fastapi.testclient import TestClient


class TestRootEndpoint:
    """
    Tests for GET /.
    """

    def test_returns_200(self, client: TestClient) -> None:
        """
        Verify root endpoint returns 200 OK.
        """
        response = client.get("/")

        assert response.status_code == 200

    def test_returns_message(self, client: TestClient) -> None:
        """
        Verify root endpoint returns message.
        """
        response = client.get("/")

        body = response.json()
        assert "message" in body

    def test_returns_docs_link(self, client: TestClient) -> None:
        """
        Verify root endpoint returns docs link.
        """
        response = client.get("/")

        body = response.json()
        assert body["docs"] == "/api-docs"

    def test_returns_json_content_type(self, client: TestClient) -> None:
        """
        Verify root endpoint returns JSON content type.
        """
        response = client.get("/")

        assert response.headers.get("content-type") == "application/json"

    def test_no_auth_required(self, client: TestClient) -> None:
        """
        Verify root endpoint does not require authentication.
        """
        response = client.get("/")

        assert response.status_code == 200
