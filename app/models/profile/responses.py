"""
Profile response models.

Constants
---------
`PROFILE_COLLECTION` is the canonical Firestore collection name for profile documents. It is
intentionally hard-coded (instead of configurable via environment variable) to reduce
configuration surface and enforce a single collection naming convention across environments.
Change here if a rename is ever required; update related tests accordingly.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.models.types import NormalizedEmail, Phone, UtcDatetime

# Firestore collection name for profiles
PROFILE_COLLECTION = "profiles"


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
