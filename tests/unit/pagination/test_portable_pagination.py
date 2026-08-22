"""Scoped canonical cursor and bidirectional item traversal tests."""

import base64
import hashlib
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from app.models.items import MOCK_ITEMS, Item
from app.pagination import InvalidCursorError, PaginationResult, decode_cursor, encode_cursor, paginate

_PORTABLE_CATALOG_SHA256 = "906c40fe3f8eea063762e2509498efe1408cb8f4da149209be4d731905ede9fd"


def _cursor_from_link(link: str, relation: str) -> str | None:
    for value in link.split(","):
        if f'rel="{relation}"' not in value:
            continue
        target = value.strip().split(">", maxsplit=1)[0].removeprefix("<")
        return parse_qs(urlsplit(target).query).get("cursor", [None])[0]
    raise AssertionError(f"missing {relation} relation")


def _page(cursor: str | None, limit: int = 10, category: str | None = None) -> PaginationResult[Item]:
    items = [item for item in MOCK_ITEMS if category is None or item.category == category]
    return paginate(
        items,
        cursor,
        limit,
        lambda item: item.id,
        "/v1/items",
        {"category": category} if category is not None else {},
    )


def test_catalog_matches_all_thirty_normative_wire_records_in_order() -> None:
    wire_catalog = [item.model_dump(mode="json", by_alias=True) for item in MOCK_ITEMS]
    canonical = json.dumps(wire_catalog, ensure_ascii=False, separators=(",", ":")).encode()
    assert len(wire_catalog) == 30
    assert hashlib.sha256(canonical).hexdigest() == _PORTABLE_CATALOG_SHA256


def test_cursor_rejects_padding_noncanonical_json_and_malformed_data() -> None:
    canonical = encode_cursor({"version": 1})
    noncanonical_json = base64.urlsafe_b64encode(b'{"version": 1}').rstrip(b"=").decode()
    for cursor in (canonical + "=", noncanonical_json, "!", "a" * 2049):
        with pytest.raises(InvalidCursorError):
            decode_cursor(cursor)


def test_three_pages_traverse_forward_and_backward_without_duplicate_or_skip() -> None:
    first = _page(None)
    second = _page(_cursor_from_link(first.link_header or "", "next"))
    third = _page(_cursor_from_link(second.link_header or "", "next"))
    assert [item.id for item in first.items + second.items + third.items] == [item.id for item in MOCK_ITEMS]
    assert 'rel="prev"' not in (first.link_header or "")

    previous_second = _page(_cursor_from_link(third.link_header or "", "prev"))
    previous_first = _page(_cursor_from_link(previous_second.link_header or "", "prev"))
    assert [item.id for item in previous_second.items] == [item.id for item in second.items]
    assert [item.id for item in previous_first.items] == [item.id for item in first.items]


def test_cursor_binds_operation_limit_filter_direction_and_anchor() -> None:
    first = _page(None, limit=5, category="electronics")
    cursor = _cursor_from_link(first.link_header or "", "next")
    assert cursor is not None
    for limit, category in ((6, "electronics"), (5, "tools"), (5, None)):
        with pytest.raises(InvalidCursorError):
            _page(cursor, limit=limit, category=category)

    state = decode_cursor(cursor)
    for mutation in (
        {**state, "operation": "other"},
        {**state, "direction": "sideways"},
        {**state, "direction": []},
        {**state, "anchor": "item-999"},
        {**state, "extra": True},
    ):
        with pytest.raises(InvalidCursorError):
            _page(encode_cursor(mutation), limit=5, category="electronics")

    one = _page(None, limit=1)
    one_state = decode_cursor(_cursor_from_link(one.link_header or "", "next") or "")
    for mutation in ({**one_state, "version": True}, {**one_state, "limit": True}):
        with pytest.raises(InvalidCursorError):
            _page(encode_cursor(mutation), limit=1)


def test_filtered_total_and_links_preserve_effective_state() -> None:
    result = _page(None, limit=2, category="robotics")
    assert result.total == 2
    assert [item.id for item in result.items] == ["item-011", "item-012"]
    assert result.link_header is None
