"""Portable profile response model and persistence collection."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.types import BoundedName, ContactEmail, OpaqueId, PhoneNumber, UTCDateTime

PROFILE_COLLECTION = "profiles"


class Profile(BaseModel):
    """Complete current-principal profile."""

    id: OpaqueId
    first_name: BoundedName = Field(alias="firstName")
    last_name: BoundedName = Field(alias="lastName")
    contact_email: ContactEmail = Field(alias="contactEmail")
    phone_number: PhoneNumber = Field(alias="phoneNumber")
    marketing_opt_in: bool = Field(alias="marketingOptIn", strict=True)
    terms_accepted: Literal[True] = Field(alias="termsAccepted")
    created_at: UTCDateTime = Field(alias="createdAt")
    updated_at: UTCDateTime = Field(alias="updatedAt")
    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> Profile:
        """Reject persisted data whose update predates creation."""
        if self.updated_at < self.created_at:
            raise ValueError("updated timestamp predates creation")
        return self
