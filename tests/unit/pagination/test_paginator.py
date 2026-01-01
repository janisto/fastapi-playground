"""Unit tests for pagination helper."""

from dataclasses import dataclass

import pytest

from app.pagination import Cursor, paginate
from app.pagination.paginator import PaginationResult


@dataclass
class MockItem:
    """Mock item for testing."""

    id: str
    name: str


def get_mock_id(item: MockItem) -> str:
    """Extract ID from mock item."""
    return item.id


def create_items(count: int) -> list[MockItem]:
    """Create a list of mock items."""
    return [MockItem(id=f"item-{i:03d}", name=f"Item {i}") for i in range(1, count + 1)]


class TestPaginationResult:
    """Tests for PaginationResult dataclass."""

    def test_has_expected_fields(self) -> None:
        """Verify PaginationResult has all expected fields."""
        result = PaginationResult(
            items=[],
            total=0,
            link_header=None,
            next_cursor=None,
            prev_cursor=None,
        )
        assert result.items == []
        assert result.total == 0
        assert result.link_header is None
        assert result.next_cursor is None
        assert result.prev_cursor is None

    def test_preserves_generic_type(self) -> None:
        """Verify PaginationResult preserves item type."""
        items = [MockItem(id="1", name="Test")]
        result: PaginationResult[MockItem] = PaginationResult(
            items=items,
            total=1,
            link_header=None,
            next_cursor=None,
            prev_cursor=None,
        )
        assert result.items[0].name == "Test"


class TestPaginateBasic:
    """Basic tests for paginate function."""

    def test_returns_all_items_when_under_limit(self) -> None:
        """Verify all items returned when count is under limit."""
        items = create_items(5)

        result = paginate(
            items=items,
            cursor=None,
            limit=10,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert len(result.items) == 5
        assert result.total == 5

    def test_returns_limited_items_when_over_limit(self) -> None:
        """Verify correct number of items returned when over limit."""
        items = create_items(20)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert len(result.items) == 5
        assert result.total == 20

    def test_empty_items_returns_empty_result(self) -> None:
        """Verify empty items list returns empty result."""
        result = paginate(
            items=[],
            cursor=None,
            limit=10,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.items == []
        assert result.total == 0
        assert result.next_cursor is None
        assert result.prev_cursor is None

    def test_returns_first_page_items(self) -> None:
        """Verify first page returns correct items."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=3,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert [i.id for i in result.items] == ["item-001", "item-002", "item-003"]


class TestPaginateCursors:
    """Tests for cursor generation."""

    def test_first_page_has_next_cursor_when_more_items(self) -> None:
        """Verify first page has next cursor when more items exist."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.next_cursor is not None
        assert result.prev_cursor is None

    def test_first_page_no_next_cursor_when_all_items_fit(self) -> None:
        """Verify first page has no next cursor when all items fit."""
        items = create_items(5)

        result = paginate(
            items=items,
            cursor=None,
            limit=10,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.next_cursor is None
        assert result.prev_cursor is None

    def test_middle_page_has_both_cursors(self) -> None:
        """Verify middle page has both next and prev cursors."""
        items = create_items(15)

        # Get cursor for second page
        first_result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        second_result = paginate(
            items=items,
            cursor=first_result.next_cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert second_result.next_cursor is not None
        assert second_result.prev_cursor is not None

    def test_last_page_has_only_prev_cursor(self) -> None:
        """Verify last page has prev cursor but no next cursor."""
        items = create_items(10)

        # Get to last page
        first_result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        last_result = paginate(
            items=items,
            cursor=first_result.next_cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert last_result.next_cursor is None
        assert last_result.prev_cursor is not None


class TestPaginateCursorNavigation:
    """Tests for cursor-based navigation."""

    def test_cursor_returns_correct_second_page(self) -> None:
        """Verify cursor returns correct items for second page."""
        items = create_items(10)

        first_result = paginate(
            items=items,
            cursor=None,
            limit=3,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        second_result = paginate(
            items=items,
            cursor=first_result.next_cursor,
            limit=3,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert [i.id for i in second_result.items] == ["item-004", "item-005", "item-006"]

    def test_cursor_returns_correct_third_page(self) -> None:
        """Verify cursor returns correct items for third page."""
        items = create_items(15)

        first_result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        second_result = paginate(
            items=items,
            cursor=first_result.next_cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        third_result = paginate(
            items=items,
            cursor=second_result.next_cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert [i.id for i in third_result.items] == [
            "item-011",
            "item-012",
            "item-013",
            "item-014",
            "item-015",
        ]

    def test_invalid_cursor_type_raises_error(self) -> None:
        """Verify cursor with wrong type raises InvalidCursorError."""
        from app.pagination import InvalidCursorError

        items = create_items(10)
        # Create cursor with different type
        cursor = Cursor(type="user", value="item-003").encode()

        with pytest.raises(InvalidCursorError, match="invalid cursor type: expected 'item'"):
            paginate(
                items=items,
                cursor=cursor,
                limit=3,
                cursor_type="item",
                get_id=get_mock_id,
                base_url="/items",
            )

    def test_nonexistent_cursor_value_starts_from_beginning(self) -> None:
        """Verify cursor with nonexistent value starts from beginning."""
        items = create_items(10)
        cursor = Cursor(type="item", value="nonexistent").encode()

        result = paginate(
            items=items,
            cursor=cursor,
            limit=3,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert [i.id for i in result.items] == ["item-001", "item-002", "item-003"]

    def test_full_pagination_traversal(self) -> None:
        """Verify complete traversal through all pages."""
        items = create_items(12)
        all_ids: list[str] = []
        cursor = None

        while True:
            result = paginate(
                items=items,
                cursor=cursor,
                limit=5,
                cursor_type="item",
                get_id=get_mock_id,
                base_url="/items",
            )
            all_ids.extend(i.id for i in result.items)

            if result.next_cursor is None:
                break
            cursor = result.next_cursor

        assert len(all_ids) == 12
        assert all_ids == [f"item-{i:03d}" for i in range(1, 13)]


class TestPaginateLinkHeader:
    """Tests for Link header generation."""

    def test_no_link_header_when_single_page(self) -> None:
        """Verify no Link header when all items fit on single page."""
        items = create_items(5)

        result = paginate(
            items=items,
            cursor=None,
            limit=10,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.link_header == ""

    def test_link_header_contains_next_rel(self) -> None:
        """Verify Link header contains rel=next for first page."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.link_header is not None
        assert 'rel="next"' in result.link_header

    def test_link_header_contains_prev_rel(self) -> None:
        """Verify Link header contains rel=prev for middle page."""
        items = create_items(15)

        first_result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        second_result = paginate(
            items=items,
            cursor=first_result.next_cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert second_result.link_header is not None
        assert 'rel="prev"' in second_result.link_header
        assert 'rel="next"' in second_result.link_header

    def test_link_header_includes_base_url(self) -> None:
        """Verify Link header includes the base URL."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/api/v1/items",
        )

        assert result.link_header is not None
        assert "/api/v1/items?" in result.link_header

    def test_link_header_includes_limit(self) -> None:
        """Verify Link header includes limit parameter."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.link_header is not None
        assert "limit=5" in result.link_header

    def test_link_header_includes_cursor(self) -> None:
        """Verify Link header includes cursor parameter."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.link_header is not None
        assert "cursor=" in result.link_header


class TestPaginateQueryParams:
    """Tests for query parameter preservation."""

    def test_preserves_single_query_param(self) -> None:
        """Verify single query param preserved in Link header."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
            query_params={"category": "electronics"},
        )

        assert result.link_header is not None
        assert "category=electronics" in result.link_header

    def test_preserves_multiple_query_params(self) -> None:
        """Verify multiple query params preserved in Link header."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
            query_params={"category": "electronics", "sort": "name"},
        )

        assert result.link_header is not None
        assert "category=electronics" in result.link_header
        assert "sort=name" in result.link_header

    def test_empty_query_params_dict(self) -> None:
        """Verify empty query params dict works correctly."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
            query_params={},
        )

        assert result.link_header is not None
        assert "limit=5" in result.link_header

    def test_none_query_params(self) -> None:
        """Verify None query params works correctly."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
            query_params=None,
        )

        assert result.link_header is not None
        assert "limit=5" in result.link_header


class TestPaginateCursorTypes:
    """Tests for different cursor types."""

    def test_different_cursor_types(self) -> None:
        """Verify pagination works with different cursor type identifiers."""
        items = create_items(10)

        for cursor_type in ["item", "user", "order", "product"]:
            result = paginate(
                items=items,
                cursor=None,
                limit=5,
                cursor_type=cursor_type,
                get_id=get_mock_id,
                base_url="/resources",
            )

            assert len(result.items) == 5
            assert result.next_cursor is not None

    def test_cursor_type_encoded_correctly(self) -> None:
        """Verify cursor type is encoded in the cursor."""
        items = create_items(10)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="custom_type",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.next_cursor is not None
        from app.pagination import decode_cursor

        decoded = decode_cursor(result.next_cursor)
        assert decoded.type == "custom_type"


class TestPaginateEdgeCases:
    """Edge case tests for paginate function."""

    def test_limit_equals_total_items(self) -> None:
        """Verify correct behavior when limit equals total items."""
        items = create_items(5)

        result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert len(result.items) == 5
        assert result.next_cursor is None
        assert result.prev_cursor is None

    def test_limit_one(self) -> None:
        """Verify pagination works with limit of 1."""
        items = create_items(3)

        result = paginate(
            items=items,
            cursor=None,
            limit=1,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert len(result.items) == 1
        assert result.items[0].id == "item-001"
        assert result.next_cursor is not None

    def test_single_item_list(self) -> None:
        """Verify pagination works with single item."""
        items = create_items(1)

        result = paginate(
            items=items,
            cursor=None,
            limit=10,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert len(result.items) == 1
        assert result.total == 1
        assert result.next_cursor is None
        assert result.prev_cursor is None

    def test_last_page_partial(self) -> None:
        """Verify last page with fewer items than limit."""
        items = create_items(7)

        first_result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        second_result = paginate(
            items=items,
            cursor=first_result.next_cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert len(second_result.items) == 2
        assert second_result.next_cursor is None

    def test_cursor_at_last_item(self) -> None:
        """Verify empty result when cursor points to last item."""
        items = create_items(5)
        cursor = Cursor(type="item", value="item-005").encode()

        result = paginate(
            items=items,
            cursor=cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.items == []
        assert result.next_cursor is None

    def test_prev_cursor_on_second_page_when_first_page_is_limit(self) -> None:
        """Verify prev cursor behavior when first page equals limit."""
        items = create_items(10)

        first_result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        second_result = paginate(
            items=items,
            cursor=first_result.next_cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert second_result.prev_cursor is not None
        from app.pagination import decode_cursor

        decoded = decode_cursor(second_result.prev_cursor)
        assert decoded.value == ""

    def test_prev_cursor_on_third_page(self) -> None:
        """Verify prev cursor on third page points to correct item."""
        items = create_items(15)

        first_result = paginate(
            items=items,
            cursor=None,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        second_result = paginate(
            items=items,
            cursor=first_result.next_cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        third_result = paginate(
            items=items,
            cursor=second_result.next_cursor,
            limit=5,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert third_result.prev_cursor is not None
        from app.pagination import decode_cursor

        decoded = decode_cursor(third_result.prev_cursor)
        assert decoded.value == "item-005"


class TestPaginateWithDifferentItemTypes:
    """Tests for paginate with different item types."""

    def test_with_dict_items(self) -> None:
        """Verify pagination works with dict items."""
        items = [{"id": f"dict-{i}", "value": i} for i in range(10)]

        result = paginate(
            items=items,
            cursor=None,
            limit=3,
            cursor_type="dict",
            get_id=lambda x: x["id"],
            base_url="/dicts",
        )

        assert len(result.items) == 3
        assert result.items[0]["id"] == "dict-0"

    def test_with_tuple_items(self) -> None:
        """Verify pagination works with tuple items."""
        items = [(f"tuple-{i}", i * 10) for i in range(10)]

        result = paginate(
            items=items,
            cursor=None,
            limit=4,
            cursor_type="tuple",
            get_id=lambda x: x[0],
            base_url="/tuples",
        )

        assert len(result.items) == 4
        assert result.items[0][0] == "tuple-0"

    def test_with_string_items(self) -> None:
        """Verify pagination works with string items."""
        items = [f"str-{i:03d}" for i in range(10)]

        result = paginate(
            items=items,
            cursor=None,
            limit=3,
            cursor_type="str",
            get_id=lambda x: x,
            base_url="/strings",
        )

        assert len(result.items) == 3
        assert result.items == ["str-000", "str-001", "str-002"]


class TestPaginateParameterized:
    """Parametrized tests for paginate function."""

    @pytest.mark.parametrize(
        ("total_items", "limit", "expected_pages"),
        [
            (10, 5, 2),
            (10, 3, 4),
            (10, 10, 1),
            (10, 1, 10),
            (15, 4, 4),
            (100, 25, 4),
        ],
    )
    def test_page_count(self, total_items: int, limit: int, expected_pages: int) -> None:
        """Verify correct number of pages for various configurations."""
        items = create_items(total_items)
        page_count = 0
        cursor = None

        while True:
            result = paginate(
                items=items,
                cursor=cursor,
                limit=limit,
                cursor_type="item",
                get_id=get_mock_id,
                base_url="/items",
            )
            page_count += 1

            if result.next_cursor is None:
                break
            cursor = result.next_cursor

        assert page_count == expected_pages

    @pytest.mark.parametrize(
        ("total_items", "limit"),
        [
            (5, 10),
            (10, 10),
            (1, 100),
            (0, 10),
        ],
    )
    def test_single_page_scenarios(self, total_items: int, limit: int) -> None:
        """Verify single page scenarios have no cursors."""
        items = create_items(total_items)

        result = paginate(
            items=items,
            cursor=None,
            limit=limit,
            cursor_type="item",
            get_id=get_mock_id,
            base_url="/items",
        )

        assert result.next_cursor is None
        assert result.prev_cursor is None
        assert result.total == total_items
