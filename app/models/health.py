"""
Health-related response models.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """
    Simple health check response.
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_url: str | None = Field(
        default=None,
        alias="$schema",
        description="JSON Schema URL for this response",
        examples=["/schemas/HealthResponse.json"],
    )
    message: Literal["healthy"] = Field(
        ...,
        description="Service health status message",
        examples=["healthy"],
    )
