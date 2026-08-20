"""Closed portable RFC 9457 Problem Details models."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ErrorSource(BaseModel):
    """One application-owned validation issue source."""

    pointer: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Application-owned JSON Pointer to an invalid body member.",
        examples=["/firstName"],
    )
    parameter: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Canonical name of an invalid query or path parameter.",
        examples=["limit"],
    )
    header: str | None = Field(
        default=None,
        min_length=1,
        max_length=256,
        description="Canonical name of an invalid request header.",
        examples=["Content-Type"],
    )
    model_config = ConfigDict(extra="forbid", strict=True)

    @model_validator(mode="after")
    def exactly_one_member(self) -> ErrorSource:
        if sum(value is not None for value in (self.pointer, self.parameter, self.header)) != 1:
            raise ValueError("exactly one source member is required")
        return self


class ValidationIssue(BaseModel):
    """Safe normalized validation issue."""

    detail: str = Field(
        min_length=1,
        max_length=200,
        description="Safe normalized explanation of one validation issue.",
        examples=["Value is invalid."],
    )
    source: ErrorSource | None = None
    model_config = ConfigDict(extra="forbid", strict=True)


class ProblemResponse(BaseModel):
    """Portable GCP Problem Details document."""

    title: str = Field(description="Stable human-readable problem title.", examples=["Validation Failed"])
    status: int = Field(description="HTTP status code for this occurrence.", examples=[422])
    detail: str = Field(
        description="Stable human-readable problem explanation.",
        examples=["Request validation failed"],
    )
    code: str = Field(
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Stable application-owned machine-readable error code.",
        examples=["validation_failed"],
    )
    errors: list[ValidationIssue] | None = Field(default=None, min_length=1, max_length=32)
    model_config = ConfigDict(extra="forbid", strict=True)
