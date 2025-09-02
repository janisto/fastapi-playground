"""Profile router for user profile management."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.firebase import FirebaseUser, security, verify_firebase_token
from app.models.error import ErrorResponse
from app.models.profile import ProfileCreate, ProfileResponse, ProfileUpdate
from app.services.profile import profile_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def _current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> FirebaseUser:
    """Resolve the current user via Firebase.

    This indirection lets tests patch ``verify_firebase_token`` in this module
    and have the change take effect at runtime.
    """
    return await verify_firebase_token(credentials)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Create user profile",
    description="Create a new profile for the authenticated user.",
    operation_id="profile_create",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Unauthorized"}}},
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden",
            "content": {"application/json": {"example": {"detail": "Forbidden"}}},
        },
        409: {
            "model": ErrorResponse,
            "description": "Profile already exists",
            "content": {"application/json": {"example": {"detail": "Profile already exists for this user"}}},
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {"application/json": {"example": {"detail": "Failed to create profile"}}},
        },
        201: {
            "description": "Profile created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Profile created successfully",
                        "profile": {
                            "id": "user-123",
                            "firstname": "John",
                            "lastname": "Doe",
                            "email": "john@example.com",
                            "phone_number": "+1234567890",
                            "marketing": True,
                            "terms": True,
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2025-01-01T00:00:00Z",
                        },
                    }
                }
            },
        },
    },
)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: Annotated[FirebaseUser, Depends(_current_user_dependency)],
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
    except HTTPException:
        # Preserve explicit HTTP error responses (e.g., 409 when already exists)
        raise
    except Exception as e:
        logger.error(f"Error creating profile for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create profile")


@router.get(
    "/",
    summary="Get user profile",
    description="Get the profile of the authenticated user.",
    operation_id="profile_get",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Unauthorized"}}},
        },
        404: {
            "model": ErrorResponse,
            "description": "Profile not found",
            "content": {"application/json": {"example": {"detail": "Profile not found"}}},
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {"application/json": {"example": {"detail": "Failed to retrieve profile"}}},
        },
        200: {
            "description": "Profile retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Profile retrieved successfully",
                        "profile": {
                            "id": "user-123",
                            "firstname": "John",
                            "lastname": "Doe",
                            "email": "john@example.com",
                            "phone_number": "+1234567890",
                            "marketing": True,
                            "terms": True,
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2025-01-01T00:00:00Z",
                        },
                    }
                }
            },
        },
    },
)
async def get_profile(
    current_user: Annotated[FirebaseUser, Depends(_current_user_dependency)],
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
    description="Update the profile of the authenticated user.",
    operation_id="profile_update",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Unauthorized"}}},
        },
        404: {
            "model": ErrorResponse,
            "description": "Profile not found",
            "content": {"application/json": {"example": {"detail": "Profile not found"}}},
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {"application/json": {"example": {"detail": "Failed to update profile"}}},
        },
        200: {
            "description": "Profile updated",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Profile updated successfully",
                        "profile": {
                            "id": "user-123",
                            "firstname": "John",
                            "lastname": "Doe",
                            "email": "john@example.com",
                            "phone_number": "+1234567890",
                            "marketing": True,
                            "terms": True,
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2025-01-01T00:00:00Z",
                        },
                    }
                }
            },
        },
    },
)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: Annotated[FirebaseUser, Depends(_current_user_dependency)],
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
    description="Delete the profile of the authenticated user.",
    operation_id="profile_delete",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Unauthorized"}}},
        },
        404: {
            "model": ErrorResponse,
            "description": "Profile not found",
            "content": {"application/json": {"example": {"detail": "Profile not found"}}},
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {"application/json": {"example": {"detail": "Failed to delete profile"}}},
        },
        200: {
            "description": "Profile deleted",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Profile deleted successfully",
                        "profile": None,
                    }
                }
            },
        },
    },
)
async def delete_profile(
    current_user: Annotated[FirebaseUser, Depends(_current_user_dependency)],
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
