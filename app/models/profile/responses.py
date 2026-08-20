"""Portable profile response model and persistence collection."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.types import BoundedName, ContactEmail, OpaqueId, PhoneNumber, UTCDateTime

PROFILE_COLLECTION = "profiles"


class Profile(BaseModel):
    """Complete current-principal profile."""

    id: OpaqueId = Field(description="Verified current-principal identifier.", examples=["principal-123"])
    first_name: BoundedName = Field(alias="firstName", description="Canonical given name.", examples=["Casey"])
    last_name: BoundedName = Field(alias="lastName", description="Canonical family name.", examples=["Morgan"])
    contact_email: ContactEmail = Field(
        alias="contactEmail",
        description="Canonical ASCII contact email.",
        examples=["Casey@example.test"],
    )
    phone_number: PhoneNumber = Field(
        alias="phoneNumber",
        description="Canonical ASCII E.164 phone number.",
        examples=["+12025550123"],
    )
    marketing_opt_in: bool = Field(
        alias="marketingOptIn",
        strict=True,
        description="Current marketing preference.",
        examples=[False],
    )
    terms_accepted: Literal[True] = Field(
        alias="termsAccepted",
        description="Confirmed terms acceptance.",
        examples=[True],
    )
    created_at: UTCDateTime = Field(
        alias="createdAt",
        description="Profile creation time in canonical UTC millisecond form.",
        examples=["2026-01-15T10:30:00.000Z"],
    )
    updated_at: UTCDateTime = Field(
        alias="updatedAt",
        description="Most recent profile mutation time in canonical UTC millisecond form.",
        examples=["2026-01-16T11:45:00.000Z"],
    )
    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> Profile:
        """Reject persisted data whose update predates creation."""
        if self.updated_at < self.created_at:
            raise ValueError("updated timestamp predates creation")
        return self
