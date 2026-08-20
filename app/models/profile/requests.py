"""Portable profile mutation models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.models.types import BoundedName, ContactEmail, PhoneNumber


class ProfileCreate(BaseModel):
    """Closed current-principal profile creation input."""

    first_name: BoundedName = Field(alias="firstName")
    last_name: BoundedName = Field(alias="lastName")
    contact_email: ContactEmail = Field(alias="contactEmail")
    phone_number: PhoneNumber = Field(alias="phoneNumber")
    marketing_opt_in: bool = Field(default=False, alias="marketingOptIn", strict=True)
    terms_accepted: Literal[True] = Field(alias="termsAccepted")
    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)


class ProfileUpdate(BaseModel):
    """Closed, non-empty current-principal profile patch input."""

    first_name: BoundedName | MISSING = Field(MISSING, alias="firstName")
    last_name: BoundedName | MISSING = Field(MISSING, alias="lastName")
    contact_email: ContactEmail | MISSING = Field(MISSING, alias="contactEmail")
    phone_number: PhoneNumber | MISSING = Field(MISSING, alias="phoneNumber")
    marketing_opt_in: bool | MISSING = Field(MISSING, alias="marketingOptIn")
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        serialize_by_alias=True,
        json_schema_extra={"minProperties": 1},
    )

    @model_validator(mode="after")
    def require_one_field(self) -> ProfileUpdate:
        """Reject an empty patch after all members validate."""
        if not self.model_fields_set:
            raise ValueError("at least one field is required")
        return self
