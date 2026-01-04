"""
Hello response models.
"""

from pydantic import BaseModel, ConfigDict, Field


class Greeting(BaseModel):
    """
    Response model for greeting endpoint.
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_url: str | None = Field(
        default=None,
        alias="$schema",
        description="JSON Schema URL for this response",
        examples=["/schemas/Greeting.json"],
    )
    message: str = Field(..., description="Greeting message", examples=["Hello, World!"])
