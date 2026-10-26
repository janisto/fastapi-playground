"""Authenticated portable current-principal profile routes."""

from fastapi import APIRouter, Request, Response, status

from app.core.constants import API_V1_PREFIX
from app.core.portable_http import PortableRoute, parse_request_model
from app.core.problems import PortableProblem
from app.dependencies import CurrentUser, ProfileServiceDependency
from app.exceptions import (
    ProfileAlreadyExistsError,
    ProfileDependencyError,
    ProfileNotFoundError,
    ProfileTimestampOverflowError,
)
from app.models.profile import Profile, ProfileCreate, ProfileUpdate

router = APIRouter(prefix=f"{API_V1_PREFIX}/profile", tags=["Profile"], route_class=PortableRoute)

_CREATE_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/ProfileCreate"}},
            "application/cbor": {"schema": {"$ref": "#/components/schemas/ProfileCreate"}},
        },
    }
}
_UPDATE_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/ProfileUpdate"}},
            "application/cbor": {"schema": {"$ref": "#/components/schemas/ProfileUpdate"}},
        },
    }
}


def _map_profile_error(error: Exception) -> PortableProblem:
    if isinstance(error, ProfileAlreadyExistsError):
        return PortableProblem("profile_exists")
    if isinstance(error, ProfileNotFoundError):
        return PortableProblem("profile_not_found")
    if isinstance(error, ProfileDependencyError):
        return PortableProblem("dependency_unavailable")
    if isinstance(error, ProfileTimestampOverflowError):
        return PortableProblem("internal_error")
    return PortableProblem("internal_error")


@router.post(
    "",
    response_model=Profile,
    status_code=status.HTTP_201_CREATED,
    summary="Create the current profile",
    description=(
        "Requires a Firebase ID token and atomically creates that principal's sole profile. Returns 201 with "
        "Location and equal creation/update timestamps; an existing profile returns 409 profile_exists. After "
        "an uncertain outcome, read and reconcile state before retrying; an existing profile does not prove "
        "the original request succeeded."
    ),
    operation_id="createProfile",
    openapi_extra=_CREATE_BODY,
)
async def create_profile(
    request: Request,
    current_user: CurrentUser,
    profile_service: ProfileServiceDependency,
    response: Response,
) -> Profile:
    """Authenticate, strictly validate, and conditionally create one profile."""
    profile_data = await parse_request_model(request, ProfileCreate)
    try:
        profile = await profile_service.create_profile(current_user.uid, profile_data)
    except (ProfileAlreadyExistsError, ProfileDependencyError, ProfileTimestampOverflowError) as error:
        raise _map_profile_error(error) from error
    response.headers["Location"] = "/v1/profile"
    return profile


@router.get(
    "",
    response_model=Profile,
    summary="Get the current profile",
    description=(
        "Requires a Firebase ID token and returns only the verified principal's profile without mutation. A "
        "missing profile returns 404 profile_not_found; this read can help reconcile an uncertain write but "
        "cannot prove which request produced the current state."
    ),
    operation_id="getProfile",
)
async def get_profile(current_user: CurrentUser, profile_service: ProfileServiceDependency) -> Profile:
    """Return the current principal profile."""
    try:
        return await profile_service.get_profile(current_user.uid)
    except (ProfileNotFoundError, ProfileDependencyError) as error:
        raise _map_profile_error(error) from error


@router.patch(
    "",
    response_model=Profile,
    summary="Update the current profile",
    description=(
        "Requires a Firebase ID token and atomically applies a non-empty patch to that principal's existing "
        "profile. Omitted fields are preserved; null is not deletion. Explicit false is accepted for "
        "marketingOptIn. Unchanged values perform no write and preserve updatedAt. After an uncertain "
        "outcome, read and reassess before replaying a patch that could overwrite intervening changes."
    ),
    operation_id="updateProfile",
    openapi_extra=_UPDATE_BODY,
)
async def update_profile(
    request: Request,
    current_user: CurrentUser,
    profile_service: ProfileServiceDependency,
) -> Profile:
    """Authenticate, validate the whole patch, and commit it atomically."""
    profile_data = await parse_request_model(request, ProfileUpdate)
    try:
        return await profile_service.update_profile(current_user.uid, profile_data)
    except (ProfileNotFoundError, ProfileDependencyError, ProfileTimestampOverflowError) as error:
        raise _map_profile_error(error) from error


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete the current profile",
    description=(
        "Requires a Firebase ID token and atomically deletes that principal's profile. Returns an empty 204, "
        "or 404 profile_not_found when absent. Repeated deletion has idempotent effects but does not replay "
        "the first response or protect a profile recreated between attempts."
    ),
    operation_id="deleteProfile",
)
async def delete_profile(current_user: CurrentUser, profile_service: ProfileServiceDependency) -> Response:
    """Delete one current-principal profile without a success representation."""
    try:
        await profile_service.delete_profile(current_user.uid)
    except (ProfileNotFoundError, ProfileDependencyError) as error:
        raise _map_profile_error(error) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
