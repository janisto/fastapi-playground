"""Portable profile mutation models."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.models.types import BoundedName, ContactEmail, PhoneNumber


class ProfileCreate(BaseModel):
    """Closed current-principal profile creation input."""

    first_name: BoundedName = Field(alias="firstName", description="Given name.", examples=["Casey"])
    last_name: BoundedName = Field(alias="lastName", description="Family name.", examples=["Morgan"])
    contact_email: ContactEmail = Field(
        alias="contactEmail",
        description="ASCII contact email; surrounding ASCII whitespace is stripped and the domain is lowercased.",
        examples=[" Casey@EXAMPLE.TEST "],
    )
    phone_number: PhoneNumber = Field(
        alias="phoneNumber",
        description="E.164 phone number after stripping surrounding ASCII whitespace.",
        examples=[" +12025550123 "],
    )
    marketing_opt_in: bool = Field(
        default=False,
        alias="marketingOptIn",
        strict=True,
        description="Current marketing preference; omitted creation input defaults to false.",
        examples=[False],
    )
    terms_accepted: Literal[True] = Field(
        alias="termsAccepted",
        description="Required confirmation that the terms are accepted.",
        examples=[True],
    )
    model_config = ConfigDict(extra="forbid", strict=True, serialize_by_alias=True)


class ProfileUpdate(BaseModel):
    """Closed, non-empty current-principal profile patch input."""

    first_name: BoundedName | MISSING = Field(
        MISSING,
        alias="firstName",
        description="Replacement given name when supplied.",
        examples=["Casey"],
    )
    last_name: BoundedName | MISSING = Field(
        MISSING,
        alias="lastName",
        description="Replacement family name when supplied.",
        examples=["Morgan"],
    )
    contact_email: ContactEmail | MISSING = Field(
        MISSING,
        alias="contactEmail",
        description="Replacement ASCII contact email after canonicalization when supplied.",
        examples=[" Casey@EXAMPLE.TEST "],
    )
    phone_number: PhoneNumber | MISSING = Field(
        MISSING,
        alias="phoneNumber",
        description="Replacement E.164 phone number after stripping ASCII whitespace when supplied.",
        examples=[" +12025550123 "],
    )
    marketing_opt_in: bool | MISSING = Field(
        MISSING,
        alias="marketingOptIn",
        description="Replacement marketing preference when supplied.",
        examples=[True],
    )
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
