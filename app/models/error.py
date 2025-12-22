"""
Shared error response models.
"""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Canonical error shape for 4xx/5xx responses.

    Keep messages non-sensitive; do not include PII or secrets.
    """

    detail: str = Field(
        ...,
        description="Error message suitable for clients",
        examples=["Profile not found"],
    )
