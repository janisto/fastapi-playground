"""Generic cursor-based pagination helper."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeVar

from app.pagination.cursor import Cursor, InvalidCursorError, decode_cursor
from app.pagination.link import build_link_header

T = TypeVar("T")


@dataclass
class PaginationResult[T]:
    """Result of pagination operation."""

    items: list[T]
    total: int
    link_header: str | None
    next_cursor: str | None
    prev_cursor: str | None


def paginate(
    items: Sequence[T],
    cursor: str | None,
    limit: int,
    cursor_type: str,
    get_id: Callable[[T], str],
    base_url: str,
    query_params: dict[str, str] | None = None,
) -> PaginationResult[T]:
    """
    Apply cursor-based pagination to a sequence of items.

    Args:
        items: Full sequence of items to paginate
        cursor: Opaque cursor string (base64 encoded type:value)
        limit: Maximum items per page
        cursor_type: Type identifier for cursor (e.g., "item", "user")
        get_id: Function to extract ID from an item
        base_url: Base URL path for Link header
        query_params: Additional query params to preserve in links

    Returns:
        PaginationResult with sliced items, total count, and Link header
    """
    query_params = query_params or {}

    # Decode cursor to determine starting position
    start_idx = 0
    if cursor:
        decoded = decode_cursor(cursor)
        if decoded.type != cursor_type:
            raise InvalidCursorError(f"invalid cursor type: expected '{cursor_type}'")
        for i, item in enumerate(items):
            if get_id(item) == decoded.value:
                start_idx = i + 1
                break

    # Get page of items
    end_idx = start_idx + limit
    page_items = list(items[start_idx:end_idx])

    # Build pagination cursors
    next_cursor = None
    prev_cursor = None

    if end_idx < len(items) and page_items:
        next_cursor = Cursor(type=cursor_type, value=get_id(page_items[-1])).encode()

    if start_idx > 0:
        if start_idx <= limit:
            prev_cursor = Cursor(type=cursor_type, value="").encode()
        else:
            prev_last_idx = start_idx - 1
            prev_cursor = Cursor(type=cursor_type, value=get_id(items[prev_last_idx - limit])).encode()

    # Build Link header
    link_header = build_link_header(
        base_url=base_url,
        query_params={**query_params, "limit": str(limit)},
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
    )

    return PaginationResult(
        items=page_items,
        total=len(items),
        link_header=link_header,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
    )
