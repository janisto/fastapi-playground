"""Deterministic local item cursor pagination."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.pagination.cursor import InvalidCursorError, decode_cursor, encode_cursor
from app.pagination.link import build_link_header


@dataclass(frozen=True, slots=True)
class PaginationResult[T]:
    """A page plus RFC 8288 navigation metadata."""

    items: list[T]
    total: int
    link_header: str | None
    next_cursor: str | None
    prev_cursor: str | None


def _item_cursor(*, direction: str, limit: int, category: str | None, anchor: str) -> str:
    return encode_cursor(
        {
            "anchor": anchor,
            "category": category,
            "direction": direction,
            "limit": limit,
            "operation": "listItems",
            "version": 1,
        }
    )


def paginate[T](
    items: Sequence[T],
    cursor: str | None,
    limit: int,
    get_id: Callable[[T], str],
    base_url: str,
    query_params: dict[str, str] | None = None,
) -> PaginationResult[T]:
    """Paginate the fixed catalog in both directions with fully scoped cursors."""
    query_params = query_params or {}
    category = query_params.get("category")
    start = 0
    if cursor is not None:
        state = decode_cursor(cursor)
        if set(state) != {"anchor", "category", "direction", "limit", "operation", "version"}:
            raise InvalidCursorError("cursor scope is invalid")
        if (
            state["operation"] != "listItems"
            or type(state["version"]) is not int
            or state["version"] != 1
            or type(state["limit"]) is not int
            or state["limit"] != limit
            or state["category"] != category
            or state["direction"] not in ("next", "prev")
            or not isinstance(state["anchor"], str)
        ):
            raise InvalidCursorError("cursor scope is invalid")
        ids = [get_id(item) for item in items]
        try:
            anchor_index = ids.index(state["anchor"])
        except ValueError as error:
            raise InvalidCursorError("cursor position is stale") from error
        start = anchor_index + 1 if state["direction"] == "next" else anchor_index

    page_items = list(items[start : start + limit])
    next_cursor = None
    prev_cursor = None
    if page_items and start + len(page_items) < len(items):
        next_cursor = _item_cursor(direction="next", limit=limit, category=category, anchor=get_id(page_items[-1]))
    if start > 0:
        previous_start = max(0, start - limit)
        if previous_start > 0:
            prev_cursor = _item_cursor(
                direction="prev", limit=limit, category=category, anchor=get_id(items[previous_start])
            )
        else:
            prev_cursor = ""

    link_header = build_link_header(
        base_url=base_url,
        query_params={**query_params, "limit": str(limit)},
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
    )
    return PaginationResult(
        items=page_items,
        total=len(items),
        link_header=link_header or None,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
    )
