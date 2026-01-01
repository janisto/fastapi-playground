"""
RFC 9457 Problem Details response models.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ValidationErrorDetail(BaseModel):
    """
    Single validation error detail.
    """

    location: str = Field(..., description="Dot-notation path to the invalid field", examples=["body.email"])
    message: str = Field(
        ..., description="Human-readable error message", examples=["value is not a valid email address"]
    )
    value: Any | None = Field(
        default=None,
        description="The invalid input value (omitted for sensitive fields)",
        examples=["not-an-email"],
    )


class ProblemResponse(BaseModel):
    """
    RFC 9457 Problem Details response schema.

    Used for OpenAPI documentation of error responses.
    Per RFC 9457, when type is omitted it defaults to "about:blank".
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_url: str | None = Field(
        default=None,
        alias="$schema",
        description="JSON Schema URL for this response",
        examples=["http://api.example.com/schemas/ErrorModel.json"],
    )
    title: str = Field(..., description="Short human-readable summary of the problem", examples=["Not Found"])
    status: int = Field(..., description="HTTP status code", examples=[404])
    detail: str = Field(..., description="Human-readable explanation", examples=["Profile not found"])


class ValidationProblemResponse(BaseModel):
    """
    RFC 9457 Problem Details with validation errors.

    Used for 422 Unprocessable Entity responses.
    Does not include 'type' field per RFC 9457 (defaults to about:blank).
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_url: str | None = Field(
        default=None,
        alias="$schema",
        description="JSON Schema URL for this response",
        examples=["http://api.example.com/schemas/ErrorModel.json"],
    )
    title: str = Field(
        default="Unprocessable Entity",
        description="Short human-readable summary of the problem",
        examples=["Unprocessable Entity"],
    )
    status: int = Field(default=422, description="HTTP status code", examples=[422])
    detail: str = Field(
        default="validation failed", description="Human-readable explanation", examples=["validation failed"]
    )
    errors: list[ValidationErrorDetail] = Field(
        default_factory=list,
        description="List of validation errors with location, message, and value",
    )
