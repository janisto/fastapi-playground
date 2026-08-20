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

    id: OpaqueId
    name: BoundedName
    category: ItemCategory
    price: Money
    in_stock: bool = Field(alias="inStock", strict=True)
    created_at: UTCDateTime = Field(alias="createdAt")
    description: str = Field(min_length=1, max_length=500, strict=True)
    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)


class ItemPage(BaseModel):
    """Current item page and filtered total."""

    items: list[Item] = Field(max_length=100)
    total: SafeInteger
    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)
