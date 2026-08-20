"""
Hello response models.
"""

from pydantic import BaseModel, ConfigDict, Field


class Greeting(BaseModel):
    """
    Response model for greeting endpoint.
    """

    message: str = Field(..., description="Greeting message", examples=["Hello, World!"])
    model_config = ConfigDict(extra="forbid", strict=True)
