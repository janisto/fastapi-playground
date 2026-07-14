"""
Integration tests for items endpoint.
"""

import cbor2
from fastapi.testclient import TestClient

from app.pagination import MAX_CURSOR_LENGTH

ITEM_FIELD_NAMES = {
    "id",
    "name",
    "category",
    "price",
    "in_stock",
    "created_at",
    "description",
}


class TestItemsList:
    """Tests for GET /v1/items."""

    def test_returns_200(self, client: TestClient) -> None:
        """Verify GET /v1/items returns 200 OK."""
        response = client.get("/v1/items")

        assert response.status_code == 200

    def test_returns_items_list(self, client: TestClient) -> None:
        """Verify GET /v1/items returns list of items."""
        response = client.get("/v1/items")

        body = response.json()
        assert "items" in body
        assert "total" in body
        assert isinstance(body["items"], list)
        assert set(body["items"][0]) == ITEM_FIELD_NAMES

    def test_response_does_not_embed_schema_metadata(self, client: TestClient) -> None:
        """Verify GET /v1/items keeps schema metadata out of the representation."""
        response = client.get("/v1/items")

        body = response.json()
        assert "$schema" not in body

    def test_returns_describedby_link_header(self, client: TestClient) -> None:
        """Verify GET /v1/items returns Link header with describedBy."""
        response = client.get("/v1/items")

        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link
        assert "/schemas/ItemList.json" in link

    def test_default_limit_is_20(self, client: TestClient) -> None:
        """Verify default limit returns 20 items."""
        response = client.get("/v1/items")

        body = response.json()
        assert len(body["items"]) == 20

    def test_custom_limit(self, client: TestClient) -> None:
        """Verify custom limit parameter works."""
        response = client.get("/v1/items", params={"limit": 5})

        body = response.json()
        assert len(body["items"]) == 5

    def test_limit_max_is_100(self, client: TestClient) -> None:
        """Verify limit over 100 returns validation error."""
        response = client.get("/v1/items", params={"limit": 101})

        assert response.status_code == 422

    def test_limit_min_is_1(self, client: TestClient) -> None:
        """Verify limit below 1 returns validation error."""
        response = client.get("/v1/items", params={"limit": 0})

        assert response.status_code == 422


class TestItemsPagination:
    """Tests for cursor-based pagination on /v1/items."""

    def test_first_page_has_link_header(self, client: TestClient) -> None:
        """Verify first page includes Link header with next."""
        response = client.get("/v1/items", params={"limit": 5})

        assert response.status_code == 200
        link = response.headers.get("link", "")
        assert 'rel="next"' in link

    def test_link_header_contains_cursor(self, client: TestClient) -> None:
        """Verify Link header contains cursor parameter."""
        response = client.get("/v1/items", params={"limit": 5})

        link = response.headers.get("link", "")
        assert "cursor=" in link

    def test_cursor_returns_next_page(self, client: TestClient) -> None:
        """Verify cursor returns correct next page items."""
        # Get first page
        response1 = client.get("/v1/items", params={"limit": 5})
        body1 = response1.json()
        first_page_ids = [item["id"] for item in body1["items"]]

        # Extract cursor from Link header
        link = response1.headers.get("link", "")
        # Parse cursor from link like: </v1/items?limit=5&cursor=xxx>; rel="next"
        import re

        match = re.search(r"cursor=([^&>]+)", link)
        assert match, "Cursor not found in Link header"
        cursor = match.group(1)

        # Get second page
        response2 = client.get("/v1/items", params={"limit": 5, "cursor": cursor})
        body2 = response2.json()
        second_page_ids = [item["id"] for item in body2["items"]]

        # Verify no overlap
        assert not set(first_page_ids) & set(second_page_ids)
        assert body2["items"][0]["id"] == "item-006"

    def test_middle_page_has_prev_and_next(self, client: TestClient) -> None:
        """Verify middle page has both prev and next links."""
        # First get first page to get the cursor
        response1 = client.get("/v1/items", params={"limit": 10})
        link1 = response1.headers.get("link", "")

        import re

        match = re.search(r"cursor=([^&>]+)", link1)
        assert match
        cursor = match.group(1)

        # Get second page
        response2 = client.get("/v1/items", params={"limit": 10, "cursor": cursor})
        link2 = response2.headers.get("link", "")

        assert 'rel="next"' in link2
        assert 'rel="prev"' in link2

    def test_last_page_has_no_next(self, client: TestClient) -> None:
        """Verify last page has no next link."""
        # Request a large limit to get all items
        response = client.get("/v1/items", params={"limit": 100})
        link = response.headers.get("link", "")

        assert 'rel="next"' not in link

    def test_third_page_has_prev_pointing_to_second_page(self, client: TestClient) -> None:
        """Verify third page prev cursor points to second page (covers start_idx > limit)."""
        import re

        # Get first page (items 1-5)
        response1 = client.get("/v1/items", params={"limit": 5})
        link1 = response1.headers.get("link", "")
        match1 = re.search(r"cursor=([^&>]+)", link1)
        assert match1
        cursor1 = match1.group(1)

        # Get second page (items 6-10)
        response2 = client.get("/v1/items", params={"limit": 5, "cursor": cursor1})
        link2 = response2.headers.get("link", "")
        match2 = re.search(r'<[^>]+cursor=([^&>]+)[^>]*>;\s*rel="next"', link2)
        assert match2
        cursor2 = match2.group(1)

        # Get third page (items 11-15) - this covers start_idx > limit branch
        response3 = client.get("/v1/items", params={"limit": 5, "cursor": cursor2})
        assert response3.status_code == 200
        body3 = response3.json()
        assert body3["items"][0]["id"] == "item-011"

        # Verify it has both prev and next links
        link3 = response3.headers.get("link", "")
        assert 'rel="prev"' in link3
        assert 'rel="next"' in link3

    def test_cursor_with_wrong_type_returns_error(self, client: TestClient) -> None:
        """Verify cursor with wrong type returns 400 Bad Request."""
        import base64

        # Create a cursor with a different type (not "item")
        cursor_value = base64.b64encode(b"other:value").decode("ascii")
        response = client.get("/v1/items", params={"cursor": cursor_value, "limit": 5})

        assert response.status_code == 400
        body = response.json()
        assert body["title"] == "Bad Request"
        assert "invalid cursor type" in body["detail"]

    def test_cursor_with_nonexistent_item_returns_error(self, client: TestClient) -> None:
        """Verify a stale item cursor returns 400 Bad Request."""
        import base64

        # Create a cursor with item type but non-existent item ID
        cursor_value = base64.b64encode(b"item:nonexistent-item").decode("ascii")
        response = client.get("/v1/items", params={"cursor": cursor_value, "limit": 5})

        assert response.status_code == 400
        body = response.json()
        assert body["title"] == "Bad Request"
        assert body["detail"] == "cursor references unknown item"

    def test_cursor_with_empty_value_returns_error(self, client: TestClient) -> None:
        """
        Verify an empty item cursor value returns 400 Bad Request.
        """
        import base64

        cursor_value = base64.b64encode(b"item:").decode("ascii")
        response = client.get("/v1/items", params={"cursor": cursor_value, "limit": 5})

        assert response.status_code == 400
        assert response.json()["detail"] == "cursor value cannot be empty"

    def test_second_page_previous_link_returns_first_page(self, client: TestClient) -> None:
        """
        Verify the first previous-page link does not require an empty cursor sentinel.
        """
        import re

        first = client.get("/v1/items", params={"limit": 5})
        next_match = re.search(r'<([^>]+)>;\s*rel="next"', first.headers["link"])
        assert next_match

        second = client.get(next_match.group(1))
        previous_match = re.search(r'<([^>]+)>;\s*rel="prev"', second.headers["link"])
        assert previous_match
        assert "cursor=" not in previous_match.group(1)

        previous = client.get(previous_match.group(1))
        assert previous.status_code == 200
        assert previous.json()["items"][0]["id"] == "item-001"


class TestItemsFiltering:
    """Tests for category filtering on /v1/items."""

    def test_category_filter_electronics(self, client: TestClient) -> None:
        """Verify category filter returns only electronics items."""
        response = client.get("/v1/items", params={"category": "electronics"})

        body = response.json()
        for item in body["items"]:
            assert item["category"] == "electronics"

    def test_category_filter_tools(self, client: TestClient) -> None:
        """Verify category filter returns only tools items."""
        response = client.get("/v1/items", params={"category": "tools"})

        body = response.json()
        assert len(body["items"]) > 0
        for item in body["items"]:
            assert item["category"] == "tools"

    def test_category_filter_accessories(self, client: TestClient) -> None:
        """Verify category filter returns only accessories items."""
        response = client.get("/v1/items", params={"category": "accessories"})

        body = response.json()
        assert len(body["items"]) > 0
        for item in body["items"]:
            assert item["category"] == "accessories"

    def test_category_filter_robotics(self, client: TestClient) -> None:
        """Verify category filter returns only robotics items."""
        response = client.get("/v1/items", params={"category": "robotics"})

        body = response.json()
        assert len(body["items"]) > 0
        for item in body["items"]:
            assert item["category"] == "robotics"

    def test_category_filter_power(self, client: TestClient) -> None:
        """Verify category filter returns only power items."""
        response = client.get("/v1/items", params={"category": "power"})

        body = response.json()
        assert len(body["items"]) > 0
        for item in body["items"]:
            assert item["category"] == "power"

    def test_category_filter_components(self, client: TestClient) -> None:
        """Verify category filter returns only components items."""
        response = client.get("/v1/items", params={"category": "components"})

        body = response.json()
        assert len(body["items"]) > 0
        for item in body["items"]:
            assert item["category"] == "components"

    def test_invalid_category_returns_422(self, client: TestClient) -> None:
        """
        Verify invalid category returns validation error.

        Per RFC 9457, validation errors use 'Unprocessable Entity' title.
        """
        response = client.get("/v1/items", params={"category": "invalid"})

        assert response.status_code == 422
        body = response.json()
        assert body["title"] == "Unprocessable Entity"
        assert body["detail"] == "validation failed"
        assert "$schema" not in body

    def test_filter_preserves_in_link_header(self, client: TestClient) -> None:
        """Verify category filter is preserved in Link header."""
        response = client.get("/v1/items", params={"category": "electronics", "limit": 5})

        link = response.headers.get("link", "")
        assert "category=electronics" in link


class TestItemsInvalidCursor:
    """Tests for invalid cursor handling on /v1/items."""

    def test_invalid_cursor_returns_400(self, client: TestClient) -> None:
        """Verify invalid cursor returns 400 Bad Request."""
        response = client.get("/v1/items", params={"cursor": "not-valid-base64!!!"})

        assert response.status_code == 400

    def test_invalid_cursor_returns_rfc9457_format(self, client: TestClient) -> None:
        """Verify invalid cursor returns RFC 9457 Problem Details format."""
        response = client.get("/v1/items", params={"cursor": "invalid!!!"})

        body = response.json()
        assert body["title"] == "Bad Request"
        assert body["status"] == 400
        assert "invalid cursor" in body["detail"]
        assert "$schema" not in body

    def test_invalid_cursor_detail_contains_error_message(self, client: TestClient) -> None:
        """Verify invalid cursor error has descriptive detail."""
        response = client.get("/v1/items", params={"cursor": "invalid!!!"})

        body = response.json()
        assert body["status"] == 400
        assert "invalid cursor" in body["detail"]

    def test_malformed_cursor_format_returns_400(self, client: TestClient) -> None:
        """Verify cursor with valid base64 but wrong format returns 400."""
        import base64

        # Valid base64 but not type:value format
        cursor = base64.urlsafe_b64encode(b"no-colon-here").decode()
        response = client.get("/v1/items", params={"cursor": cursor})

        assert response.status_code == 400
        body = response.json()
        assert body["title"] == "Bad Request"

    def test_oversized_cursor_returns_400(self, client: TestClient) -> None:
        """Verify cursor length violations remain malformed parameters, not 422 validation errors."""
        response = client.get(
            "/v1/items",
            params={"cursor": "x" * (MAX_CURSOR_LENGTH + 1)},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "cursor exceeds maximum length"

    def test_invalid_cursor_cbor_returns_cbor_problem(self, client: TestClient) -> None:
        """Verify invalid cursor with Accept: application/cbor returns CBOR error."""
        response = client.get(
            "/v1/items",
            params={"cursor": "invalid!!!"},
            headers={"Accept": "application/cbor"},
        )

        assert response.status_code == 400
        assert "cbor" in response.headers["content-type"]
        decoded = cbor2.loads(response.content)
        assert decoded["title"] == "Bad Request"
        assert decoded["status"] == 400


class TestItemsCBOR:
    """Tests for CBOR content negotiation on /v1/items."""

    def test_accept_cbor_returns_cbor(self, client: TestClient) -> None:
        """Verify Accept: application/cbor returns CBOR response."""
        response = client.get("/v1/items", headers={"Accept": "application/cbor"})

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/cbor"
        decoded = cbor2.loads(response.content)
        assert "items" in decoded
        assert "total" in decoded
        assert set(decoded["items"][0]) == ITEM_FIELD_NAMES
