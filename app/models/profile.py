"""Profile data models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ProfileBase(BaseModel):
    """Base profile model with common fields."""

    firstname: str = Field(..., min_length=1, max_length=100, description="The first name of the user")
    lastname: str = Field(..., min_length=1, max_length=100, description="The last name of the user")
    email: EmailStr = Field(..., description="The email address of the user")
    phone_number: str = Field(..., min_length=1, max_length=20, description="The phone number of the user")
    marketing: bool = Field(
        default=False, description="Indicates if the user has opted in for marketing communications"
    )
    terms: bool = Field(..., description="Indicates if the user has accepted the terms and conditions")


class ProfileCreate(ProfileBase):
    """Model for creating a new profile."""

    pass


class ProfileUpdate(BaseModel):
    """Model for updating an existing profile."""

    firstname: Optional[str] = Field(None, min_length=1, max_length=100, description="The first name of the user")
    lastname: Optional[str] = Field(None, min_length=1, max_length=100, description="The last name of the user")
    email: Optional[EmailStr] = Field(None, description="The email address of the user")
    phone_number: Optional[str] = Field(None, min_length=1, max_length=20, description="The phone number of the user")
    marketing: Optional[bool] = Field(
        None, description="Indicates if the user has opted in for marketing communications"
    )
    terms: Optional[bool] = Field(None, description="Indicates if the user has accepted the terms and conditions")


class Profile(ProfileBase):
    """Complete profile model with metadata."""

    id: str = Field(..., description="The unique identifier for the profile")
    created_at: datetime = Field(..., description="The date and time when the profile was created")
    updated_at: datetime = Field(..., description="The date and time when the profile was last updated")

    model_config = {
        "from_attributes": True,
    }


class ProfileResponse(BaseModel):
    """Response model for profile operations."""

    success: bool = Field(..., description="Indicates if the operation was successful")
    message: str = Field(..., description="A message describing the result")
    profile: Optional[Profile] = Field(None, description="The profile data if available")
