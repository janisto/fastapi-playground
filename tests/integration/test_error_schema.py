"""
Integration tests for $schema field on error responses.

Verifies that all RFC 9457 error responses include $schema and Link header
as required by the API guidelines.
"""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from tests.helpers.profiles import make_profile_payload_dict

ERROR_SCHEMA_PATH = "/schemas/ErrorModel.json"


class TestErrorSchemaOn4xxResponses:
    """Tests for $schema on 4xx error responses."""

    def test_401_includes_schema(
        self,
        client: TestClient,
    ) -> None:
        """Verify 401 Unauthorized includes $schema."""
        response = client.get("/profile/")

        assert response.status_code == 401
        body = response.json()
        assert "$schema" in body
        assert ERROR_SCHEMA_PATH in body["$schema"]

    def test_401_includes_link_header(
        self,
        client: TestClient,
    ) -> None:
        """Verify 401 includes Link header with describedBy."""
        response = client.get("/profile/")

        assert response.status_code == 401
        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link
        assert ERROR_SCHEMA_PATH in link

    def test_404_includes_schema(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """Verify 404 Not Found includes $schema."""
        mock_profile_service.get_profile.side_effect = ProfileNotFoundError()

        response = client.get("/profile/")

        assert response.status_code == 404
        body = response.json()
        assert "$schema" in body
        assert ERROR_SCHEMA_PATH in body["$schema"]

    def test_404_includes_link_header(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """Verify 404 includes Link header with describedBy."""
        mock_profile_service.get_profile.side_effect = ProfileNotFoundError()

        response = client.get("/profile/")

        assert response.status_code == 404
        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link

    def test_409_includes_schema(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """Verify 409 Conflict includes $schema."""
        mock_profile_service.create_profile.side_effect = ProfileAlreadyExistsError()

        response = client.post("/profile/", json=make_profile_payload_dict())

        assert response.status_code == 409
        body = response.json()
        assert "$schema" in body
        assert ERROR_SCHEMA_PATH in body["$schema"]

    def test_422_validation_error_includes_schema(
        self,
        client: TestClient,
        with_fake_user: None,
    ) -> None:
        """Verify 422 validation error includes $schema."""
        response = client.post("/profile/", json={"invalid": "data"})

        assert response.status_code == 422
        body = response.json()
        assert "$schema" in body
        assert ERROR_SCHEMA_PATH in body["$schema"]

    def test_422_validation_error_includes_link_header(
        self,
        client: TestClient,
        with_fake_user: None,
    ) -> None:
        """Verify 422 validation error includes Link header."""
        response = client.post("/profile/", json={"invalid": "data"})

        assert response.status_code == 422
        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link


class TestErrorSchemaOn5xxResponses:
    """Tests for $schema on 5xx error responses."""

    def test_500_includes_schema(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """Verify 500 Internal Server Error includes $schema."""
        mock_profile_service.get_profile.side_effect = RuntimeError("Database failure")

        response = client.get("/profile/")

        assert response.status_code == 500
        body = response.json()
        assert "$schema" in body
        assert ERROR_SCHEMA_PATH in body["$schema"]

    def test_500_includes_link_header(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """Verify 500 includes Link header with describedBy."""
        mock_profile_service.get_profile.side_effect = RuntimeError("Database failure")

        response = client.get("/profile/")

        assert response.status_code == 500
        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link


class TestErrorSchemaFormat:
    """Tests for $schema URL format compliance."""

    def test_schema_is_absolute_url(
        self,
        client: TestClient,
    ) -> None:
        """Verify $schema is an absolute URL per JSON Schema spec."""
        response = client.get("/profile/")

        assert response.status_code == 401
        body = response.json()
        schema_url = body["$schema"]
        assert schema_url.startswith(("http://", "https://"))

    def test_schema_url_contains_host(
        self,
        client: TestClient,
    ) -> None:
        """Verify $schema URL includes the host."""
        response = client.get("/profile/")

        body = response.json()
        schema_url = body["$schema"]
        assert "testserver" in schema_url or "localhost" in schema_url

    def test_link_header_uses_relative_path(
        self,
        client: TestClient,
    ) -> None:
        """Verify Link header uses relative path for portability."""
        response = client.get("/profile/")

        link = response.headers.get("link", "")
        assert f"<{ERROR_SCHEMA_PATH}>" in link
