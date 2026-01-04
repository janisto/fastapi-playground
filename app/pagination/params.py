"""
Shared pagination parameter types.
"""

from typing import Annotated

from fastapi import Query

CursorParam = Annotated[str | None, Query(description="Opaque pagination cursor")]
LimitParam = Annotated[int, Query(ge=1, le=100, description="Items per page")]
