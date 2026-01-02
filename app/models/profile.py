"""
Profile data models.

Constants
---------
`PROFILE_COLLECTION` is the canonical Firestore collection name for profile documents. It is
intentionally hard-coded (instead of configurable via environment variable) to reduce
configuration surface and enforce a single collection naming convention across environments.
Change here if a rename is ever required; update related tests accordingly.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.types import NormalizedEmail, Phone, UtcDatetime

# Firestore collection name for profiles
PROFILE_COLLECTION = "profiles"


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


class Profile(BaseModel):
    """
    Complete profile model with metadata.

    Note: Does not inherit from ProfileBase to avoid extra="forbid" which is
    inappropriate for response models.
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_url: str | None = Field(
        default=None,
        alias="$schema",
        description="JSON Schema URL for this response",
        examples=["/schemas/ProfileData.json"],
    )
    id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique identifier",
        examples=["user-abc123"],
    )
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
    created_at: UtcDatetime = Field(
        ...,
        description="Creation timestamp",
        examples=["2025-01-15T10:30:00.000Z"],
    )
    updated_at: UtcDatetime = Field(
        ...,
        description="Last update timestamp",
        examples=["2025-01-15T10:30:00.000Z"],
    )
