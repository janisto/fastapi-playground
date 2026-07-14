"""
Profile request models.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.experimental.missing_sentinel import MISSING

from app.models.types import NormalizedEmail, Phone


class ProfileBase(BaseModel):
    """
    Base profile model with common fields.
    """

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="First name",
        examples=["John"],
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Last name",
        examples=["Doe"],
    )
    email: NormalizedEmail = Field(
        ...,
        description="Email address (auto-lowercased)",
        examples=["user@example.com"],
    )
    phone_number: Phone = Field(
        ...,
        description="Phone number",
        examples=["+358401234567"],
    )
    marketing: bool = Field(
        default=False,
        description="Marketing opt-in",
        examples=[False],
    )
    terms: bool = Field(
        ...,
        description="Terms acceptance",
        examples=[True],
    )

    model_config = ConfigDict(extra="forbid")


class ProfileCreate(ProfileBase):
    """
    Model for creating a new profile.

    Validates that terms must be accepted (True) on profile creation.
    """

    @field_validator("terms", mode="after")
    @classmethod
    def terms_must_be_accepted(cls, value: bool) -> bool:
        """
        Enforce terms acceptance on profile creation.
        """
        if not value:
            raise ValueError("terms must be accepted")
        return value


class ProfileUpdate(BaseModel):
    """
    Model for updating an existing profile.
    """

    first_name: str | MISSING = Field(
        MISSING,
        min_length=1,
        max_length=100,
        description="First name",
        examples=["John"],
    )
    last_name: str | MISSING = Field(
        MISSING,
        min_length=1,
        max_length=100,
        description="Last name",
        examples=["Doe"],
    )
    email: NormalizedEmail | MISSING = Field(
        MISSING,
        description="Email address (auto-lowercased)",
        examples=["user@example.com"],
    )
    phone_number: Phone | MISSING = Field(
        MISSING,
        description="Phone number",
        examples=["+358401234567"],
    )
    marketing: bool | MISSING = Field(
        MISSING,
        description="Marketing opt-in",
        examples=[False],
    )

    model_config = ConfigDict(extra="forbid")
