"""Profile request models."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.types import NormalizedEmail, Phone


class ProfileBase(BaseModel):
    """
    Base profile model with common fields.
    """

    firstname: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="First name",
        examples=["John"],
    )
    lastname: str = Field(
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
    def terms_must_be_accepted(cls, v: bool) -> bool:
        """Enforce terms acceptance on profile creation."""
        if not v:
            raise ValueError("terms must be accepted")
        return v


class ProfileUpdate(BaseModel):
    """
    Model for updating an existing profile.
    """

    firstname: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="First name",
        examples=["John"],
    )
    lastname: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Last name",
        examples=["Doe"],
    )
    email: NormalizedEmail | None = Field(
        None,
        description="Email address (auto-lowercased)",
        examples=["user@example.com"],
    )
    phone_number: Phone | None = Field(
        None,
        description="Phone number",
        examples=["+358401234567"],
    )
    marketing: bool | None = Field(
        None,
        description="Marketing opt-in",
        examples=[False],
    )
    terms: bool | None = Field(
        None,
        description="Terms acceptance",
        examples=[True],
    )

    model_config = ConfigDict(extra="forbid")
