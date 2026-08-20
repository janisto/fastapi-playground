"""Portable deterministic item collection."""

from fastapi import APIRouter, Request, Response

from app.core.constants import API_V1_PREFIX
from app.core.portable_http import PortableRoute, request_query
from app.core.problems import PortableProblem
from app.models.items import MOCK_ITEMS, ItemPage
from app.pagination import InvalidCursorError, paginate

_CATEGORIES = frozenset({"electronics", "tools", "accessories", "robotics", "power", "components"})
_MAX_LIMIT = 100

router = APIRouter(prefix=f"{API_V1_PREFIX}/items", tags=["Items"], route_class=PortableRoute)


@router.get(
    "",
    response_model=ItemPage,
    summary="List catalog items",
    description="Filters and cursor-paginates the fixed portable catalog.",
    operation_id="listItems",
)
async def list_items(request: Request, response: Response) -> ItemPage:
    """Return one deterministic item page and navigation links."""
    query = request_query(request)
    limit = int(query.get("limit", "20"))
    if not 1 <= limit <= _MAX_LIMIT:
        raise PortableProblem(
            "validation_failed",
            errors=[{"detail": "Request field is invalid", "source": {"parameter": "limit"}}],
        )
    category_value = query.get("category")
    if category_value is not None and category_value not in _CATEGORIES:
        raise PortableProblem(
            "validation_failed",
            errors=[{"detail": "Request field is invalid", "source": {"parameter": "category"}}],
        )
    category = category_value
    filtered_items = [item for item in MOCK_ITEMS if category is None or item.category == category]
    try:
        result = paginate(
            items=filtered_items,
            cursor=query.get("cursor"),
            limit=limit,
            get_id=lambda item: item.id,
            base_url="/v1/items",
            query_params={"category": category} if category is not None else {},
        )
    except InvalidCursorError as error:
        raise PortableProblem("invalid_request") from error
    if result.link_header:
        response.headers["Link"] = result.link_header
    return ItemPage(items=result.items, total=result.total)
