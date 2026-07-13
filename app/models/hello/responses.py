"""
Hello response models.
"""

from pydantic import BaseModel, Field


class Greeting(BaseModel):
    """
    Response model for greeting endpoint.
    """

    message: str = Field(..., description="Greeting message", examples=["Hello, World!"])
