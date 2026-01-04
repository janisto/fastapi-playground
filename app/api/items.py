"""
Items router demonstrating pagination and filtering.

This router provides example endpoints showing:
- Cursor-based pagination
- RFC 8288 Link headers for navigation
- Literal type for category filter
- Limit validation with min/max
- CBOR content negotiation
"""

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response

from app.core.cbor import CBORRoute
from app.models.error import ProblemResponse, ValidationProblemResponse
from app.models.items import MOCK_ITEMS, VALID_CATEGORIES, ItemList
from app.pagination import CursorParam, LimitParam, paginate

router = APIRouter(
    prefix="/items",
    tags=["Items"],
    route_class=CBORRoute,
    responses={
        422: {"model": ValidationProblemResponse, "description": "Validation error"},
        500: {"model": ProblemResponse, "description": "Server error"},
    },
)


@router.get(
    "",
    summary="List items",
    description="Returns a paginated list of items with optional category filter.",
    operation_id="items_list",
    responses={
        200: {"model": ItemList, "description": "Items retrieved successfully"},
    },
)
async def list_items(
    request: Request,
    response: Response,
    cursor: CursorParam = None,
    limit: LimitParam = 20,
    category: Annotated[
        VALID_CATEGORIES | None,
        Query(description="Filter by category"),
    ] = None,
) -> ItemList:
    """
    List items with cursor-based pagination.

    Demonstrates:
    - Cursor-based pagination with type:value format
    - RFC 8288 Link headers for prev/next navigation
    - Literal type for category filter validation
    - Limit validation (1-100 range)
    """
    # Filter items by category if specified
    filtered_items = MOCK_ITEMS
    if category:
        filtered_items = [item for item in MOCK_ITEMS if item.category == category]

    # Build query params to preserve in pagination links
    query_params: dict[str, str] = {}
    if category:
        query_params["category"] = category

    # Apply pagination
    result = paginate(
        items=filtered_items,
        cursor=cursor,
        limit=limit,
        cursor_type="item",
        get_id=lambda item: item.id,
        base_url=str(request.url.path).rstrip("/"),
        query_params=query_params,
    )

    # Build Link headers (pagination + describedBy for JSON Schema)
    links: list[str] = []
    if result.link_header:
        links.append(result.link_header)
    links.append('</schemas/ItemList.json>; rel="describedBy"')
    response.headers["Link"] = ", ".join(links)

    return ItemList(
        schema_url=str(request.base_url) + "schemas/ItemList.json",
        items=result.items,
        total=result.total,
    )
