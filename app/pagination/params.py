"""
Shared pagination parameter types.
"""

from typing import Annotated

from fastapi import Query

from app.pagination.cursor import MAX_CURSOR_LENGTH

CursorParam = Annotated[
    str | None,
    Query(
        description="Opaque pagination cursor",
        json_schema_extra={"maxLength": MAX_CURSOR_LENGTH},
    ),
]
LimitParam = Annotated[int, Query(ge=1, le=100, description="Items per page")]
