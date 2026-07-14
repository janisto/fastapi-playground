"""
Integration tests for JSON Schema discovery endpoints.
"""

import cbor2
import pytest
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

    @pytest.mark.parametrize("accept", ["application/schema+json", "application/*", "*/*"])
    def test_accepts_schema_representation_ranges(self, accept: str) -> None:
        """
        Verify exact and wildcard ranges can select the schema representation.
        """
        response = client.get("/schemas/HealthResponse.json", headers={"Accept": accept})

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/schema+json"

    @pytest.mark.parametrize(
        ("accept", "problem_media_type"),
        [
            ("application/json", "application/problem+json"),
            ("application/cbor", "application/cbor"),
            ("application/problem+json", "application/problem+json"),
            ("application/problem+cbor", "application/problem+json"),
            ("application/xml", "application/problem+json"),
            ("application/schema+json;q=0, */*;q=1", "application/problem+json"),
        ],
    )
    def test_rejects_ranges_that_exclude_schema_representation(
        self,
        accept: str,
        problem_media_type: str,
    ) -> None:
        """
        Verify schema discovery honors strict Accept ranges and exact exclusions.
        """
        response = client.get("/schemas/HealthResponse.json", headers={"Accept": accept})

        assert response.status_code == 406
        assert response.headers["content-type"] == problem_media_type
        assert response.headers["Vary"] == "Accept"
        body = cbor2.loads(response.content) if problem_media_type == "application/cbor" else response.json()
        assert body["title"] == "Not Acceptable"
        assert body["detail"] == "Supported response formats: application/schema+json"

    def test_rejects_unacceptable_representation_before_schema_lookup(self) -> None:
        """
        Verify success negotiation takes precedence over route-specific lookup.
        """
        response = client.get("/schemas/NonExistent.json", headers={"Accept": "application/cbor"})

        assert response.status_code == 406
        assert cbor2.loads(response.content)["title"] == "Not Acceptable"

    def test_returns_schema_with_properties(self) -> None:
        response = client.get("/schemas/HealthResponse.json")
        data = response.json()

        assert "properties" in data
        assert "type" in data
        assert data["type"] == "object"
        assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"

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
        assert data["properties"]["items"]["items"]["$ref"] == "#/$defs/Item"
        assert "Item" in data["$defs"]

    def test_profile_schema_exists(self) -> None:
        response = client.get("/schemas/Profile.json")

        assert response.status_code == 200
        data = response.json()
        assert "properties" in data

    def test_problem_schemas_exist(self) -> None:
        problem = client.get("/schemas/ProblemResponse.json")
        validation = client.get("/schemas/ValidationProblemResponse.json")

        assert problem.status_code == 200
        assert validation.status_code == 200
        assert "ValidationErrorDetail" in validation.json()["$defs"]


class TestSchemaNotInOpenAPI:
    """Tests that schema endpoint is hidden from OpenAPI."""

    def test_schemas_endpoint_not_in_openapi(self) -> None:
        response = client.get("/openapi.json")
        openapi = response.json()

        paths = openapi.get("paths", {})
        schema_paths = [p for p in paths if p.startswith("/schemas")]

        assert len(schema_paths) == 0
