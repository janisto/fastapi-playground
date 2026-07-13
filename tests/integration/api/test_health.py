"""
Integration tests for health endpoint.
"""

import cbor2
import pytest
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

    def test_response_does_not_embed_schema_metadata(self, client: TestClient) -> None:
        """
        Verify health representation omits schema metadata.
        """
        response = client.get("/health")

        body = response.json()
        assert "$schema" not in body

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

    @pytest.mark.parametrize(
        ("accept", "problem_media_type"),
        [
            ("application/cbor", "application/problem+cbor"),
            ("application/xml", "application/problem+json"),
        ],
    )
    def test_rejects_unsupported_success_media_types(
        self,
        client: TestClient,
        accept: str,
        problem_media_type: str,
    ) -> None:
        """
        Verify the JSON-only health representation enforces Accept negotiation.
        """
        response = client.get("/health", headers={"Accept": accept})

        assert response.status_code == 406
        assert response.headers["content-type"] == problem_media_type
        body = cbor2.loads(response.content) if problem_media_type == "application/problem+cbor" else response.json()
        assert body["detail"] == "Supported response formats: application/json"
