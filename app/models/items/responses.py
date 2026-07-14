"""
Items response models.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.types import UTCDateTime

ItemCategory = Literal["electronics", "tools", "accessories", "robotics", "power", "components"]


class Item(BaseModel):
    """
    An item in the inventory.
    """

    id: str = Field(..., description="Unique item identifier", examples=["item-001"])
    name: str = Field(..., description="Item name", examples=["Alpha Widget"])
    category: ItemCategory = Field(..., description="Item category", examples=["electronics"])
    price: float = Field(..., ge=0, description="Item price in USD", examples=[29.99])
    in_stock: bool = Field(..., description="Availability status", examples=[True])
    created_at: UTCDateTime = Field(..., description="Creation timestamp", examples=["2024-01-15T10:30:00.000Z"])
    description: str = Field(
        ..., description="Detailed description of the item", examples=["A versatile electronic widget for everyday use"]
    )


class ItemList(BaseModel):
    """
    Paginated list of items.
    """

    items: list[Item] = Field(..., description="List of items in current page")
    total: int = Field(..., ge=0, description="Total number of items matching filter", examples=[30])
