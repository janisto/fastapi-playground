"""
Integration tests for hello endpoint.
"""

import cbor2
from fastapi.testclient import TestClient


class TestHelloGet:
    """Tests for GET /hello/."""

    def test_returns_200(self, client: TestClient) -> None:
        """Verify GET /hello/ returns 200 OK."""
        response = client.get("/hello/")

        assert response.status_code == 200

    def test_returns_greeting_message(self, client: TestClient) -> None:
        """Verify GET /hello/ returns greeting message."""
        response = client.get("/hello/")

        body = response.json()
        assert body["message"] == "Hello, World!"

    def test_returns_schema_url(self, client: TestClient) -> None:
        """Verify GET /hello/ returns $schema URL."""
        response = client.get("/hello/")

        body = response.json()
        assert "$schema" in body
        assert "schemas/HelloData.json" in body["$schema"]

    def test_returns_describedby_link_header(self, client: TestClient) -> None:
        """Verify GET /hello/ returns Link header with describedBy."""
        response = client.get("/hello/")

        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link
        assert "/schemas/HelloData.json" in link

    def test_returns_json_by_default(self, client: TestClient) -> None:
        """Verify GET /hello/ returns JSON content type."""
        response = client.get("/hello/")

        assert "application/json" in response.headers.get("content-type", "")

    def test_accepts_cbor_negotiation(self, client: TestClient) -> None:
        """Verify GET /hello/ returns CBOR when requested."""
        response = client.get("/hello/", headers={"Accept": "application/cbor"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/cbor"
        decoded = cbor2.loads(response.content)
        assert decoded["message"] == "Hello, World!"


class TestHelloPost:
    """Tests for POST /hello/."""

    def test_returns_201_created(self, client: TestClient) -> None:
        """Verify POST /hello/ returns 201 Created."""
        response = client.post("/hello/", json={"name": "Alice"})

        assert response.status_code == 201

    def test_returns_location_header(self, client: TestClient) -> None:
        """Verify POST /hello/ includes Location header."""
        response = client.post("/hello/", json={"name": "Alice"})

        assert response.headers.get("location") == "/hello/"

    def test_returns_schema_url(self, client: TestClient) -> None:
        """Verify POST /hello/ returns $schema URL."""
        response = client.post("/hello/", json={"name": "Alice"})

        body = response.json()
        assert "$schema" in body
        assert "schemas/HelloData.json" in body["$schema"]

    def test_returns_describedby_link_header(self, client: TestClient) -> None:
        """Verify POST /hello/ returns Link header with describedBy."""
        response = client.post("/hello/", json={"name": "Alice"})

        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link
        assert "/schemas/HelloData.json" in link

    def test_returns_personalized_greeting(self, client: TestClient) -> None:
        """Verify POST /hello/ returns personalized greeting."""
        response = client.post("/hello/", json={"name": "Alice"})

        body = response.json()
        assert body["message"] == "Hello, Alice!"

    def test_supports_language_parameter(self, client: TestClient) -> None:
        """Verify POST /hello/ supports language parameter."""
        response = client.post("/hello/", json={"name": "Alice", "language": "fi"})

        body = response.json()
        assert body["message"] == "Hei, Alice!"

    def test_invalid_language_returns_422(self, client: TestClient) -> None:
        """Verify invalid language code returns validation error."""
        response = client.post("/hello/", json={"name": "Bob", "language": "xx"})

        assert response.status_code == 422
        body = response.json()
        assert body["status"] == 422
        assert len(body["errors"]) == 1
        assert body["errors"][0]["location"] == "body.language"

    def test_accepts_cbor_request(self, client: TestClient) -> None:
        """Verify POST /hello/ accepts CBOR request body."""
        payload = cbor2.dumps({"name": "Alice"})

        response = client.post(
            "/hello/",
            content=payload,
            headers={"Content-Type": "application/cbor"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["message"] == "Hello, Alice!"

    def test_cbor_request_with_cbor_response(self, client: TestClient) -> None:
        """Verify CBOR request and response works end-to-end."""
        payload = cbor2.dumps({"name": "Alice"})

        response = client.post(
            "/hello/",
            content=payload,
            headers={
                "Content-Type": "application/cbor",
                "Accept": "application/cbor",
            },
        )

        assert response.status_code == 201
        assert response.headers["content-type"] == "application/cbor"
        decoded = cbor2.loads(response.content)
        assert decoded["message"] == "Hello, Alice!"


class TestHelloValidation:
    """
    Tests for validation errors on /hello/.

    Per RFC 9457, validation errors use 'Unprocessable Entity' title
    and 'type' is omitted (defaults to about:blank).
    """

    def test_empty_name_returns_422(self, client: TestClient) -> None:
        """Verify empty name returns 422 validation error."""
        response = client.post("/hello/", json={"name": ""})

        assert response.status_code == 422
        body = response.json()
        assert body["title"] == "Unprocessable Entity"
        assert body["status"] == 422
        assert body["detail"] == "validation failed"
        assert "errors" in body

    def test_missing_name_returns_422(self, client: TestClient) -> None:
        """Verify missing name returns 422 validation error."""
        response = client.post("/hello/", json={})

        assert response.status_code == 422
        body = response.json()
        assert body["title"] == "Unprocessable Entity"
        assert "errors" in body
        assert any("name" in e.get("location", "") for e in body["errors"])

    def test_extra_field_returns_422(self, client: TestClient) -> None:
        """Verify extra field returns 422 (extra=forbid)."""
        response = client.post("/hello/", json={"name": "Alice", "unknown": "field"})

        assert response.status_code == 422
        body = response.json()
        assert body["title"] == "Unprocessable Entity"
        assert "errors" in body

    def test_validation_error_has_structured_format(self, client: TestClient) -> None:
        """
        Verify validation errors use structured format with errors array.

        Per RFC 9457, 'type' is omitted when about:blank (the default).
        """
        response = client.post("/hello/", json={"name": ""})

        body = response.json()
        assert "type" not in body  # RFC 9457: type omitted when about:blank
        assert body["title"] == "Unprocessable Entity"
        assert body["status"] == 422
        assert body["detail"] == "validation failed"
        assert "errors" in body
        assert "$schema" in body
        error = body["errors"][0]
        assert "location" in error
        assert "message" in error
