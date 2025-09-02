"""Shared error response models."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Canonical error shape for 4xx/5xx responses.

    Keep messages non-sensitive; do not include PII or secrets.
    """

    detail: str = Field(..., description="Error message suitable for clients")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"detail": "Unauthorized"},
                {"detail": "Profile not found"},
                {"detail": "Failed to create profile"},
            ]
        }
    }
