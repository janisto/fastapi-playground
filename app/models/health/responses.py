"""
Health response models.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """
    Simple health check response.
    """

    status: Literal["healthy"] = Field(
        ...,
        description="Service health status",
        examples=["healthy"],
    )
    model_config = ConfigDict(extra="forbid", strict=True)
