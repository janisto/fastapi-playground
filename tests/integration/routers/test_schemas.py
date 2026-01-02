"""
Integration tests for JSON Schema discovery endpoints.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


class TestGetSchema:
    """Tests for GET /schemas/{schema_name}."""

    def test_returns_200_for_valid_schema(self) -> None:
        response = client.get("/schemas/HealthResponse.json")

        assert response.status_code == 200

    def test_returns_schema_json_content_type(self) -> None:
        response = client.get("/schemas/HealthResponse.json")

        assert response.headers["content-type"] == "application/schema+json"

    def test_returns_schema_with_properties(self) -> None:
        response = client.get("/schemas/HealthResponse.json")
        data = response.json()

        assert "properties" in data
        assert "type" in data
        assert data["type"] == "object"

    def test_works_without_json_extension(self) -> None:
        response = client.get("/schemas/HealthResponse")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/schema+json"

    def test_returns_404_for_nonexistent_schema(self) -> None:
        response = client.get("/schemas/NonExistent.json")

        assert response.status_code == 404

    def test_404_returns_problem_json(self) -> None:
        response = client.get("/schemas/NonExistent.json")

        assert response.headers["content-type"] == "application/problem+json"
        data = response.json()
        assert data["title"] == "Schema not found"
        assert data["status"] == 404

    def test_404_includes_schema_name_in_detail(self) -> None:
        response = client.get("/schemas/NonExistent.json")
        data = response.json()

        assert "NonExistent" in data["detail"]


class TestSchemaContent:
    """Tests for schema content accuracy."""

    def test_greeting_schema_has_message_property(self) -> None:
        response = client.get("/schemas/Greeting.json")
        data = response.json()

        assert "message" in data["properties"]

    def test_item_list_schema_has_items_and_total(self) -> None:
        response = client.get("/schemas/ItemList.json")
        data = response.json()

        assert "items" in data["properties"]
        assert "total" in data["properties"]

    def test_profile_schema_exists(self) -> None:
        response = client.get("/schemas/Profile.json")

        assert response.status_code == 200
        data = response.json()
        assert "properties" in data


class TestSchemaNotInOpenAPI:
    """Tests that schema endpoint is hidden from OpenAPI."""

    def test_schemas_endpoint_not_in_openapi(self) -> None:
        response = client.get("/openapi.json")
        openapi = response.json()

        paths = openapi.get("paths", {})
        schema_paths = [p for p in paths if p.startswith("/schemas")]

        assert len(schema_paths) == 0
