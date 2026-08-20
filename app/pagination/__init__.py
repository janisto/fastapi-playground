"""
Pagination utilities.
"""

from app.pagination.cursor import MAX_CURSOR_LENGTH, InvalidCursorError, decode_cursor, encode_cursor
from app.pagination.link import build_link_header
from app.pagination.paginator import PaginationResult, paginate
from app.pagination.params import CursorParam, LimitParam

__all__ = [
    "MAX_CURSOR_LENGTH",
    "CursorParam",
    "InvalidCursorError",
    "LimitParam",
    "PaginationResult",
    "build_link_header",
    "decode_cursor",
    "encode_cursor",
    "paginate",
]
