"""Closed portable RFC 9457 Problem Details models."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ErrorSource(BaseModel):
    """One application-owned validation issue source."""

    pointer: str | None = Field(default=None, min_length=1, max_length=256)
    parameter: str | None = Field(default=None, min_length=1, max_length=256)
    header: str | None = Field(default=None, min_length=1, max_length=256)
    model_config = ConfigDict(extra="forbid", strict=True)

    @model_validator(mode="after")
    def exactly_one_member(self) -> ErrorSource:
        if sum(value is not None for value in (self.pointer, self.parameter, self.header)) != 1:
            raise ValueError("exactly one source member is required")
        return self


class ValidationIssue(BaseModel):
    """Safe normalized validation issue."""

    detail: str = Field(min_length=1, max_length=200)
    source: ErrorSource | None = None
    model_config = ConfigDict(extra="forbid", strict=True)


class ProblemResponse(BaseModel):
    """Portable GCP Problem Details document."""

    title: str
    status: int
    detail: str
    code: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    errors: list[ValidationIssue] | None = Field(default=None, min_length=1, max_length=32)
    model_config = ConfigDict(extra="forbid", strict=True)
