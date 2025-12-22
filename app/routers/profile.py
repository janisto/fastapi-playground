"""
Profile router for user profile management.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, ProfileServiceDep
from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from app.models.error import ErrorResponse
from app.models.profile import ProfileCreate, ProfileResponse, ProfileUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ProfileResponse,
    summary="Create user profile",
    description="Create a new profile for the authenticated user.",
    operation_id="profile_create",
    responses={
        201: {"model": ProfileResponse, "description": "Profile created successfully"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        409: {"model": ErrorResponse, "description": "Profile already exists"},
    },
)
async def create_profile(
    profile_data: ProfileCreate,
    current_user: CurrentUser,
    service: ProfileServiceDep,
) -> ProfileResponse:
    """
    Create a new profile for the authenticated user.

    Stores the profile data in Firestore under the user's UID.
    Returns 409 Conflict if a profile already exists.
    """
    try:
        profile = await service.create_profile(current_user.uid, profile_data)
        return ProfileResponse(success=True, message="Profile created successfully", profile=profile)
    except (HTTPException, ProfileAlreadyExistsError):
        raise
    except Exception:
        logger.exception("Error creating profile for user %s", current_user.uid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create profile"
        ) from None


@router.get(
    "/",
    response_model=ProfileResponse,
    summary="Get user profile",
    description="Get the profile of the authenticated user.",
    operation_id="profile_get",
    responses={
        200: {"model": ProfileResponse, "description": "Profile retrieved successfully"},
        404: {"model": ErrorResponse, "description": "Profile not found"},
    },
)
async def get_profile(
    current_user: CurrentUser,
    service: ProfileServiceDep,
) -> ProfileResponse:
    """
    Retrieve the profile of the authenticated user.

    Returns 404 Not Found if no profile exists for the user.
    """
    try:
        profile = await service.get_profile(current_user.uid)
        return ProfileResponse(success=True, message="Profile retrieved successfully", profile=profile)
    except (HTTPException, ProfileNotFoundError):
        raise
    except Exception:
        logger.exception("Error getting profile for user %s", current_user.uid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve profile"
        ) from None


@router.patch(
    "/",
    response_model=ProfileResponse,
    response_model_exclude_unset=True,
    summary="Update user profile",
    description="Partially update the profile of the authenticated user.",
    operation_id="profile_update",
    responses={
        200: {"model": ProfileResponse, "description": "Profile updated successfully"},
        404: {"model": ErrorResponse, "description": "Profile not found"},
    },
)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: CurrentUser,
    service: ProfileServiceDep,
) -> ProfileResponse:
    """
    Partially update the profile of the authenticated user.

    Only the fields explicitly provided in the request are updated.
    Omitted fields retain their existing values.
    Returns 404 Not Found if no profile exists for the user.
    """
    try:
        profile = await service.update_profile(current_user.uid, profile_data)
        return ProfileResponse(success=True, message="Profile updated successfully", profile=profile)
    except (HTTPException, ProfileNotFoundError):
        raise
    except Exception:
        logger.exception("Error updating profile for user %s", current_user.uid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile"
        ) from None


@router.delete(
    "/",
    response_model=ProfileResponse,
    summary="Delete user profile",
    description="Delete the profile of the authenticated user.",
    operation_id="profile_delete",
    responses={
        200: {"model": ProfileResponse, "description": "Profile deleted successfully"},
        404: {"model": ErrorResponse, "description": "Profile not found"},
    },
)
async def delete_profile(
    current_user: CurrentUser,
    service: ProfileServiceDep,
) -> ProfileResponse:
    """
    Delete the profile of the authenticated user.

    Permanently removes the profile from Firestore.
    Returns 404 Not Found if no profile exists for the user.
    """
    try:
        await service.delete_profile(current_user.uid)
        return ProfileResponse(success=True, message="Profile deleted successfully", profile=None)
    except (HTTPException, ProfileNotFoundError):
        raise
    except Exception:
        logger.exception("Error deleting profile for user %s", current_user.uid)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete profile"
        ) from None
