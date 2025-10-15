"""Dog data models.

Constants
---------
`DOG_COLLECTION` is the canonical Firestore collection name for dog documents. It is
intentionally hard-coded (instead of configurable via environment variable) to reduce
configuration surface and enforce a single collection naming convention across environments.
Change here if a rename is ever required; update related tests accordingly.
"""

from datetime import datetime

from pydantic import BaseModel, Field

# Firestore collection name for dogs
DOG_COLLECTION = "dogs"


class DogBase(BaseModel):
    """Base dog model with common fields."""

    name: str = Field(..., min_length=1, max_length=100, description="The name of the dog")
    breed: str = Field(..., min_length=1, max_length=100, description="The breed of the dog")
    age: int = Field(..., ge=0, le=30, description="The age of the dog in years")
    color: str | None = Field(None, max_length=50, description="The color of the dog")
    weight_kg: float | None = Field(None, ge=0, le=200, description="The weight of the dog in kilograms")

    model_config = {
        "extra": "forbid",
    }


class DogCreate(DogBase):
    """Model for creating a new dog."""

    pass


class DogUpdate(BaseModel):
    """Model for updating an existing dog."""

    name: str | None = Field(None, min_length=1, max_length=100, description="The name of the dog")
    breed: str | None = Field(None, min_length=1, max_length=100, description="The breed of the dog")
    age: int | None = Field(None, ge=0, le=30, description="The age of the dog in years")
    color: str | None = Field(None, max_length=50, description="The color of the dog")
    weight_kg: float | None = Field(None, ge=0, le=200, description="The weight of the dog in kilograms")

    model_config = {
        "extra": "forbid",
    }


class Dog(DogBase):
    """Complete dog model with metadata."""

    id: str = Field(..., min_length=1, max_length=128, description="The unique identifier for the dog")
    owner_uid: str = Field(..., min_length=1, max_length=128, description="The Firebase user ID of the dog's owner")
    created_at: datetime = Field(..., description="The date and time when the dog was created")
    updated_at: datetime = Field(..., description="The date and time when the dog was last updated")

    model_config = {
        "from_attributes": True,
    }


class DogResponse(BaseModel):
    """Response model for dog operations."""

    success: bool = Field(..., description="Indicates if the operation was successful")
    message: str = Field(..., description="A message describing the result")
    dog: Dog | None = Field(None, description="The dog data if available")


class DogListResponse(BaseModel):
    """Response model for listing dogs."""

    success: bool = Field(..., description="Indicates if the operation was successful")
    message: str = Field(..., description="A message describing the result")
    dogs: list[Dog] = Field(default_factory=list, description="List of dogs")
    count: int = Field(..., description="Total number of dogs returned")
