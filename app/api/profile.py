"""
Profile router for user profile management.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.core.cbor import CBORRoute
from app.dependencies import CurrentUser, ProfileServiceDep
from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from app.models.error import ProblemResponse, ValidationProblemResponse
from app.models.profile import Profile, ProfileCreate, ProfileUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
    route_class=CBORRoute,
    responses={
        401: {"model": ProblemResponse, "description": "Unauthorized"},
        422: {"model": ValidationProblemResponse, "description": "Validation error"},
        500: {"model": ProblemResponse, "description": "Server error"},
    },
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create user profile",
    description="Create a new profile for the authenticated user.",
    operation_id="profile_create",
    responses={
        201: {"model": Profile, "description": "Profile created successfully"},
        409: {"model": ProblemResponse, "description": "Profile already exists"},
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
        response.headers["Link"] = '</schemas/ProfileData.json>; rel="describedBy"'
        return Profile(
            schema_url=str(request.base_url) + "schemas/ProfileData.json",
            id=profile.id,
            firstname=profile.firstname,
            lastname=profile.lastname,
            email=profile.email,
            phone_number=profile.phone_number,
            marketing=profile.marketing,
            terms=profile.terms,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
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
        200: {"model": Profile, "description": "Profile retrieved successfully"},
        404: {"model": ProblemResponse, "description": "Profile not found"},
    },
)
async def get_profile(
    request: Request,
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
        response.headers["Link"] = '</schemas/ProfileData.json>; rel="describedBy"'
        return Profile(
            schema_url=str(request.base_url) + "schemas/ProfileData.json",
            id=profile.id,
            firstname=profile.firstname,
            lastname=profile.lastname,
            email=profile.email,
            phone_number=profile.phone_number,
            marketing=profile.marketing,
            terms=profile.terms,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
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
        200: {"model": Profile, "description": "Profile updated successfully"},
        404: {"model": ProblemResponse, "description": "Profile not found"},
    },
)
async def update_profile(
    request: Request,
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
        response.headers["Link"] = '</schemas/ProfileData.json>; rel="describedBy"'
        return Profile(
            schema_url=str(request.base_url) + "schemas/ProfileData.json",
            id=profile.id,
            firstname=profile.firstname,
            lastname=profile.lastname,
            email=profile.email,
            phone_number=profile.phone_number,
            marketing=profile.marketing,
            terms=profile.terms,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
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
        204: {"description": "Profile deleted successfully"},
        404: {"model": ProblemResponse, "description": "Profile not found"},
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
