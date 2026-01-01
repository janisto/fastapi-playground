"""Unit tests for Link header builder."""

from app.pagination import build_link_header


class TestBuildLinkHeader:
    """Tests for build_link_header function."""

    def test_next_only(self) -> None:
        """Test building Link header with only next cursor."""
        result = build_link_header(
            base_url="/items",
            query_params={},
            next_cursor="abc123",
            prev_cursor=None,
        )
        assert result == '</items?cursor=abc123>; rel="next"'

    def test_prev_only(self) -> None:
        """Test building Link header with only prev cursor."""
        result = build_link_header(
            base_url="/items",
            query_params={},
            next_cursor=None,
            prev_cursor="xyz789",
        )
        assert result == '</items?cursor=xyz789>; rel="prev"'

    def test_both_cursors(self) -> None:
        """Test building Link header with both cursors."""
        result = build_link_header(
            base_url="/items",
            query_params={},
            next_cursor="next123",
            prev_cursor="prev456",
        )
        assert 'rel="next"' in result
        assert 'rel="prev"' in result
        assert "cursor=next123" in result
        assert "cursor=prev456" in result

    def test_no_cursors(self) -> None:
        """Test building Link header with no cursors returns empty string."""
        result = build_link_header(
            base_url="/items",
            query_params={},
            next_cursor=None,
            prev_cursor=None,
        )
        assert result == ""

    def test_preserves_query_params(self) -> None:
        """Test that existing query parameters are preserved."""
        result = build_link_header(
            base_url="/items",
            query_params={"category": "books", "limit": "10"},
            next_cursor="abc123",
            prev_cursor=None,
        )
        assert "category=books" in result
        assert "limit=10" in result
        assert "cursor=abc123" in result

    def test_url_encodes_special_characters(self) -> None:
        """Test that special characters are URL encoded."""
        result = build_link_header(
            base_url="/items",
            query_params={"filter": "hello world"},
            next_cursor="abc+123",
            prev_cursor=None,
        )
        assert "filter=hello+world" in result or "filter=hello%20world" in result
        assert "cursor=abc%2B123" in result

    def test_multiple_query_params_order(self) -> None:
        """Test Link header format with multiple query params."""
        result = build_link_header(
            base_url="/api/v1/users",
            query_params={"status": "active"},
            next_cursor="cursor_next",
            prev_cursor="cursor_prev",
        )
        parts = result.split(", ")
        assert len(parts) == 2
        assert parts[0].endswith('; rel="next"')
        assert parts[1].endswith('; rel="prev"')
