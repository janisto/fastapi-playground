"""Portable item response models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.types import BoundedName, OpaqueId, SafeInteger, UTCDateTime

ItemCategory = Literal["electronics", "tools", "accessories", "robotics", "power", "components"]


class Money(BaseModel):
    """Exact USD amount in integer minor units."""

    amount_minor: SafeInteger = Field(alias="amountMinor", description="Amount in US cents", examples=[2999])
    currency: Literal["USD"] = Field(description="ISO currency", examples=["USD"])
    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)


class Item(BaseModel):
    """One fixed-catalog item."""

    id: OpaqueId = Field(description="Opaque catalog item identifier.", examples=["precision-screwdriver"])
    name: BoundedName = Field(description="Catalog item name.", examples=["Precision Screwdriver"])
    category: ItemCategory = Field(description="Catalog category.", examples=["tools"])
    price: Money
    in_stock: bool = Field(alias="inStock", strict=True, description="Whether the item is in stock.", examples=[True])
    created_at: UTCDateTime = Field(
        alias="createdAt",
        description="Catalog creation time in canonical UTC millisecond form.",
        examples=["2026-01-15T10:30:00.000Z"],
    )
    description: str = Field(
        min_length=1,
        max_length=500,
        strict=True,
        description="Catalog item description.",
        examples=["A hardened precision screwdriver."],
    )
    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)


class ItemPage(BaseModel):
    """Current item page and filtered total."""

    items: list[Item] = Field(max_length=100)
    total: SafeInteger = Field(description="Total number of items matching the current filter.", examples=[6])
    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)
