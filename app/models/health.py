"""
Health-related response models.
"""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """
    Simple health check response.
    """

    status: Literal["healthy"] = Field(
        ...,
        description="Service health status",
        examples=["healthy"],
    )
