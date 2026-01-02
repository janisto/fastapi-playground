"""
Items router demonstrating pagination and filtering.

This router provides example endpoints showing:
- Cursor-based pagination
- RFC 8288 Link headers for navigation
- Literal type for category filter
- Limit validation with min/max
- CBOR content negotiation
"""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.core.cbor import CBORRoute
from app.models.error import ProblemResponse, ValidationProblemResponse
from app.models.types import UtcDatetime
from app.pagination import CursorParam, LimitParam, paginate

VALID_CATEGORIES = Literal["electronics", "tools", "accessories", "robotics", "power", "components"]


class Item(BaseModel):
    """An item in the inventory."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    schema_url: str | None = Field(
        default=None,
        alias="$schema",
        serialization_alias="$schema",
        description="JSON Schema URL for this response",
        examples=["/schemas/Item.json"],
        exclude_if=lambda v: v is None,
    )
    id: str = Field(..., description="Unique item identifier", examples=["item-001"])
    name: str = Field(..., description="Item name", examples=["Alpha Widget"])
    category: VALID_CATEGORIES = Field(..., description="Item category", examples=["electronics"])
    price: float = Field(..., ge=0, description="Item price in USD", examples=[29.99])
    in_stock: bool = Field(..., description="Availability status", examples=[True])
    created_at: UtcDatetime = Field(..., description="Creation timestamp", examples=["2024-01-15T10:30:00.000Z"])
    description: str = Field(
        ..., description="Detailed description of the item", examples=["A versatile electronic widget for everyday use"]
    )


class ItemList(BaseModel):
    """Paginated list of items."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_url: str | None = Field(
        default=None,
        alias="$schema",
        description="JSON Schema URL for this response",
        examples=["/schemas/ItemList.json"],
    )
    items: list[Item] = Field(..., description="List of items in current page")
    total: int = Field(..., ge=0, description="Total number of items matching filter", examples=[30])


# Mock data for demonstration
MOCK_ITEMS: list[Item] = [
    Item(
        id="item-001",
        name="Alpha Widget",
        category="electronics",
        price=29.99,
        in_stock=True,
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        description="A versatile electronic widget for everyday use",
    ),
    Item(
        id="item-002",
        name="Beta Gadget",
        category="electronics",
        price=49.99,
        in_stock=True,
        created_at=datetime(2024, 1, 16, 11, 0, 0, tzinfo=UTC),
        description="Advanced gadget with smart features",
    ),
    Item(
        id="item-003",
        name="Gamma Tool",
        category="tools",
        price=15.50,
        in_stock=False,
        created_at=datetime(2024, 1, 17, 9, 15, 0, tzinfo=UTC),
        description="Precision tool for professional work",
    ),
    Item(
        id="item-004",
        name="Delta Component",
        category="electronics",
        price=8.99,
        in_stock=True,
        created_at=datetime(2024, 1, 18, 14, 45, 0, tzinfo=UTC),
        description="Essential component for electronics projects",
    ),
    Item(
        id="item-005",
        name="Epsilon Sensor",
        category="electronics",
        price=34.99,
        in_stock=True,
        created_at=datetime(2024, 1, 19, 8, 0, 0, tzinfo=UTC),
        description="High-precision environmental sensor",
    ),
    Item(
        id="item-006",
        name="Zeta Cable",
        category="accessories",
        price=12.99,
        in_stock=True,
        created_at=datetime(2024, 1, 20, 16, 30, 0, tzinfo=UTC),
        description="Premium quality data cable",
    ),
    Item(
        id="item-007",
        name="Eta Adapter",
        category="accessories",
        price=9.99,
        in_stock=False,
        created_at=datetime(2024, 1, 21, 10, 0, 0, tzinfo=UTC),
        description="Universal power adapter",
    ),
    Item(
        id="item-008",
        name="Theta Board",
        category="electronics",
        price=89.99,
        in_stock=True,
        created_at=datetime(2024, 1, 22, 11, 30, 0, tzinfo=UTC),
        description="Development board for prototyping",
    ),
    Item(
        id="item-009",
        name="Iota Switch",
        category="electronics",
        price=5.99,
        in_stock=True,
        created_at=datetime(2024, 1, 23, 9, 45, 0, tzinfo=UTC),
        description="Tactile push button switch",
    ),
    Item(
        id="item-010",
        name="Kappa Display",
        category="electronics",
        price=45.99,
        in_stock=True,
        created_at=datetime(2024, 1, 24, 13, 0, 0, tzinfo=UTC),
        description="OLED display module",
    ),
    Item(
        id="item-011",
        name="Lambda Motor",
        category="robotics",
        price=24.99,
        in_stock=True,
        created_at=datetime(2024, 1, 25, 8, 30, 0, tzinfo=UTC),
        description="DC motor for robotics projects",
    ),
    Item(
        id="item-012",
        name="Mu Servo",
        category="robotics",
        price=18.99,
        in_stock=False,
        created_at=datetime(2024, 1, 26, 15, 0, 0, tzinfo=UTC),
        description="High-torque servo motor",
    ),
    Item(
        id="item-013",
        name="Nu Battery",
        category="power",
        price=14.99,
        in_stock=True,
        created_at=datetime(2024, 1, 27, 10, 15, 0, tzinfo=UTC),
        description="Rechargeable lithium battery pack",
    ),
    Item(
        id="item-014",
        name="Xi Charger",
        category="power",
        price=22.99,
        in_stock=True,
        created_at=datetime(2024, 1, 28, 11, 45, 0, tzinfo=UTC),
        description="Smart battery charger",
    ),
    Item(
        id="item-015",
        name="Omicron Relay",
        category="electronics",
        price=7.99,
        in_stock=True,
        created_at=datetime(2024, 1, 29, 9, 0, 0, tzinfo=UTC),
        description="5V relay module",
    ),
    Item(
        id="item-016",
        name="Pi Controller",
        category="electronics",
        price=55.99,
        in_stock=True,
        created_at=datetime(2024, 1, 30, 14, 30, 0, tzinfo=UTC),
        description="Microcontroller board",
    ),
    Item(
        id="item-017",
        name="Rho Resistor Kit",
        category="components",
        price=11.99,
        in_stock=True,
        created_at=datetime(2024, 2, 1, 8, 0, 0, tzinfo=UTC),
        description="Assorted resistor pack",
    ),
    Item(
        id="item-018",
        name="Sigma Capacitor Set",
        category="components",
        price=13.99,
        in_stock=True,
        created_at=datetime(2024, 2, 2, 10, 30, 0, tzinfo=UTC),
        description="Electrolytic capacitor assortment",
    ),
    Item(
        id="item-019",
        name="Tau LED Pack",
        category="components",
        price=6.99,
        in_stock=True,
        created_at=datetime(2024, 2, 3, 11, 0, 0, tzinfo=UTC),
        description="Multi-color LED assortment",
    ),
    Item(
        id="item-020",
        name="Upsilon Wire Set",
        category="accessories",
        price=8.99,
        in_stock=False,
        created_at=datetime(2024, 2, 4, 9, 15, 0, tzinfo=UTC),
        description="Jumper wire kit",
    ),
    Item(
        id="item-021",
        name="Phi Breadboard",
        category="tools",
        price=4.99,
        in_stock=True,
        created_at=datetime(2024, 2, 5, 13, 45, 0, tzinfo=UTC),
        description="Solderless breadboard",
    ),
    Item(
        id="item-022",
        name="Chi Soldering Iron",
        category="tools",
        price=35.99,
        in_stock=True,
        created_at=datetime(2024, 2, 6, 10, 0, 0, tzinfo=UTC),
        description="Temperature-controlled soldering station",
    ),
    Item(
        id="item-023",
        name="Psi Multimeter",
        category="tools",
        price=42.99,
        in_stock=True,
        created_at=datetime(2024, 2, 7, 11, 30, 0, tzinfo=UTC),
        description="Digital multimeter with auto-ranging",
    ),
    Item(
        id="item-024",
        name="Omega Oscilloscope",
        category="tools",
        price=299.99,
        in_stock=True,
        created_at=datetime(2024, 2, 8, 14, 0, 0, tzinfo=UTC),
        description="Portable digital oscilloscope",
    ),
    Item(
        id="item-025",
        name="Alpha Pro Widget",
        category="electronics",
        price=59.99,
        in_stock=True,
        created_at=datetime(2024, 2, 9, 8, 30, 0, tzinfo=UTC),
        description="Professional-grade widget with extended features",
    ),
    Item(
        id="item-026",
        name="Beta Max Gadget",
        category="electronics",
        price=79.99,
        in_stock=False,
        created_at=datetime(2024, 2, 10, 9, 0, 0, tzinfo=UTC),
        description="Maximum performance gadget",
    ),
    Item(
        id="item-027",
        name="Gamma Plus Tool",
        category="tools",
        price=25.99,
        in_stock=True,
        created_at=datetime(2024, 2, 11, 10, 15, 0, tzinfo=UTC),
        description="Enhanced precision tool",
    ),
    Item(
        id="item-028",
        name="Delta Ultra Component",
        category="electronics",
        price=16.99,
        in_stock=True,
        created_at=datetime(2024, 2, 12, 11, 45, 0, tzinfo=UTC),
        description="Ultra-reliable component",
    ),
    Item(
        id="item-029",
        name="Epsilon HD Sensor",
        category="electronics",
        price=54.99,
        in_stock=True,
        created_at=datetime(2024, 2, 13, 13, 0, 0, tzinfo=UTC),
        description="High-definition sensor array",
    ),
    Item(
        id="item-030",
        name="Zeta Premium Cable",
        category="accessories",
        price=19.99,
        in_stock=True,
        created_at=datetime(2024, 2, 14, 15, 30, 0, tzinfo=UTC),
        description="Gold-plated premium cable",
    ),
]


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
