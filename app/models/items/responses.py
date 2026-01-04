"""
Items response models.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.models.types import UtcDatetime

VALID_CATEGORIES = Literal["electronics", "tools", "accessories", "robotics", "power", "components"]


class Item(BaseModel):
    """
    An item in the inventory.
    """

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
    """
    Paginated list of items.
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_url: str | None = Field(
        default=None,
        alias="$schema",
        description="JSON Schema URL for this response",
        examples=["/schemas/ItemList.json"],
    )
    items: list[Item] = Field(..., description="List of items in current page")
    total: int = Field(..., ge=0, description="Total number of items matching filter", examples=[30])
