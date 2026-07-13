"""
Profile router for user profile management.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.cbor import CBORRoute
from app.core.constants import API_V1_PREFIX
from app.core.openapi import COMMON_CBOR_RESPONSES, empty_response, problem_response, success_response
from app.core.schema_links import build_described_by_link
from app.dependencies import CurrentUser, ProfileServiceDep
from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from app.models.error import ValidationProblemResponse
from app.models.profile import Profile, ProfileCreate, ProfileUpdate

logger = logging.getLogger(__name__)
PROFILE_SCHEMA_PATH = "/schemas/Profile.json"

router = APIRouter(
    prefix=f"{API_V1_PREFIX}/profile",
    tags=["Profile"],
    route_class=CBORRoute,
    responses={
        **COMMON_CBOR_RESPONSES,
        401: problem_response("Unauthorized", authenticate=True),
        503: problem_response("Authentication service unavailable", retry_after=True),
    },
)


def _profile_response(response: Response, profile: Profile) -> Profile:
    """
    Add profile schema discovery metadata to a response model.
    """
    response.headers["Link"] = build_described_by_link(PROFILE_SCHEMA_PATH)
    return profile


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create user profile",
    description="Create a new profile for the authenticated user.",
    operation_id="profile_create",
    responses={
        201: success_response("Profile created successfully", "Profile", location=True),
        409: problem_response("Profile already exists"),
        422: problem_response("Validation error", model=ValidationProblemResponse),
    },
)
async def create_profile(
    request: Request,
    profile_data: ProfileCreate,
    current_user: CurrentUser,
    service: ProfileServiceDep,
    response: Response,
) -> Profile:
    """
    Create a new profile for the authenticated user.

    Stores the profile data in Firestore under the user's UID.
    Returns 409 Conflict if a profile already exists.
    """
    try:
        profile = await service.create_profile(current_user.uid, profile_data)
        response.headers["Location"] = str(request.url.path)
        return _profile_response(response, profile)
    except HTTPException, ProfileAlreadyExistsError:
        raise
    except Exception:
        logger.exception("Error creating profile", extra={"user_id": current_user.uid})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create profile"
        ) from None


@router.get(
    "",
    summary="Get user profile",
    description="Get the profile of the authenticated user.",
    operation_id="profile_get",
    responses={
        200: success_response("Profile retrieved successfully", "Profile"),
        404: problem_response("Profile not found"),
    },
)
async def get_profile(
    response: Response,
    current_user: CurrentUser,
    service: ProfileServiceDep,
) -> Profile:
    """
    Retrieve the profile of the authenticated user.

    Returns 404 Not Found if no profile exists for the user.
    """
    try:
        profile = await service.get_profile(current_user.uid)
        return _profile_response(response, profile)
    except HTTPException, ProfileNotFoundError:
        raise
    except Exception:
        logger.exception("Error getting profile", extra={"user_id": current_user.uid})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve profile"
        ) from None


@router.patch(
    "",
    response_model=Profile,
    response_model_exclude_unset=True,
    summary="Update user profile",
    description="Partially update the profile of the authenticated user.",
    operation_id="profile_update",
    responses={
        200: success_response("Profile updated successfully", "Profile"),
        404: problem_response("Profile not found"),
        422: problem_response("Validation error", model=ValidationProblemResponse),
    },
)
async def update_profile(
    response: Response,
    profile_data: ProfileUpdate,
    current_user: CurrentUser,
    service: ProfileServiceDep,
) -> Profile:
    """
    Partially update the profile of the authenticated user.

    Only the fields explicitly provided in the request are updated.
    Omitted fields retain their existing values.
    Returns 404 Not Found if no profile exists for the user.
    """
    try:
        profile = await service.update_profile(current_user.uid, profile_data)
        return _profile_response(response, profile)
    except HTTPException, ProfileNotFoundError:
        raise
    except Exception:
        logger.exception("Error updating profile", extra={"user_id": current_user.uid})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update profile"
        ) from None


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user profile",
    description="Delete the profile of the authenticated user.",
    operation_id="profile_delete",
    responses={
        204: empty_response("Profile deleted successfully"),
        404: problem_response("Profile not found"),
    },
)
async def delete_profile(
    current_user: CurrentUser,
    service: ProfileServiceDep,
) -> None:
    """
    Delete the profile of the authenticated user.

    Permanently removes the profile from Firestore.
    Returns 404 Not Found if no profile exists for the user.
    """
    try:
        await service.delete_profile(current_user.uid)
    except HTTPException, ProfileNotFoundError:
        raise
    except Exception:
        logger.exception("Error deleting profile", extra={"user_id": current_user.uid})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete profile"
        ) from None
