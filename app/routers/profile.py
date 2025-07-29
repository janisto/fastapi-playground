"""Profile router for user profile management."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.firebase import FirebaseUser, verify_firebase_token
from app.models.profile import ProfileCreate, ProfileResponse, ProfileUpdate
from app.services.profile import profile_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create user profile",
    description="Create a new profile for the authenticated user",
)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: Annotated[FirebaseUser, Depends(verify_firebase_token)],
) -> ProfileResponse:
    """
    Create a new profile for the authenticated user.

    Args:
        profile_data: The profile data to create
        current_user: The authenticated Firebase user

    Returns:
        ProfileResponse: The response with created profile

    Raises:
        HTTPException: If profile already exists or creation fails
    """
    try:
        # Check if profile already exists
        existing_profile = await profile_service.get_profile(current_user.uid)
        if existing_profile:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists for this user")

        # Create new profile
        profile = await profile_service.create_profile(current_user.uid, profile_data)

        return ProfileResponse(success=True, message="Profile created successfully", profile=profile)

    except ValueError as e:
        logger.warning(f"Profile creation failed for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating profile for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create profile")


@router.get(
    "/",
    summary="Get user profile",
    description="Get the profile of the authenticated user",
)
async def get_profile(
    current_user: Annotated[FirebaseUser, Depends(verify_firebase_token)],
) -> ProfileResponse:
    """
    Get the profile of the authenticated user.

    Args:
        current_user: The authenticated Firebase user

    Returns:
        ProfileResponse: The response with user profile

    Raises:
        HTTPException: If profile not found
    """
    try:
        profile = await profile_service.get_profile(current_user.uid)

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

        return ProfileResponse(success=True, message="Profile retrieved successfully", profile=profile)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting profile for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve profile")


@router.put(
    "/",
    summary="Update user profile",
    description="Update the profile of the authenticated user",
)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: Annotated[FirebaseUser, Depends(verify_firebase_token)],
) -> ProfileResponse:
    """
    Update the profile of the authenticated user.

    Args:
        profile_data: The profile data to update
        current_user: The authenticated Firebase user

    Returns:
        ProfileResponse: The response with updated profile

    Raises:
        HTTPException: If profile not found or update fails
    """
    try:
        profile = await profile_service.update_profile(current_user.uid, profile_data)

        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

        return ProfileResponse(success=True, message="Profile updated successfully", profile=profile)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile")


@router.delete(
    "/",
    summary="Delete user profile",
    description="Delete the profile of the authenticated user",
)
async def delete_profile(
    current_user: Annotated[FirebaseUser, Depends(verify_firebase_token)],
) -> ProfileResponse:
    """
    Delete the profile of the authenticated user.

    Args:
        current_user: The authenticated Firebase user

    Returns:
        ProfileResponse: The response confirming deletion

    Raises:
        HTTPException: If profile not found or deletion fails
    """
    try:
        success = await profile_service.delete_profile(current_user.uid)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

        return ProfileResponse(success=True, message="Profile deleted successfully", profile=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profile for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete profile")
