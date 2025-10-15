"""Dog router for dog management."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.firebase import FirebaseUser, security, verify_firebase_token
from app.models.dog import DogCreate, DogListResponse, DogResponse, DogUpdate
from app.models.error import ErrorResponse
from app.services.dog import dog_service

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
    summary="Create a dog",
    description="Create a new dog entry for the authenticated user.",
    operation_id="dog_create",
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
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {"application/json": {"example": {"detail": "Failed to create dog"}}},
        },
        201: {
            "description": "Dog created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Dog created successfully",
                        "dog": {
                            "id": "dog-123",
                            "owner_uid": "user-123",
                            "name": "Buddy",
                            "breed": "Golden Retriever",
                            "age": 3,
                            "color": "Golden",
                            "weight_kg": 30.5,
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2025-01-01T00:00:00Z",
                        },
                    }
                }
            },
        },
    },
)
async def create_dog(
    dog_data: DogCreate,
    current_user: Annotated[FirebaseUser, Depends(_current_user_dependency)],
) -> DogResponse:
    """
    Create a new dog for the authenticated user.

    Args:
        dog_data: The dog data to create
        current_user: The authenticated Firebase user

    Returns:
        DogResponse: The response with created dog

    Raises:
        HTTPException: If creation fails
    """
    try:
        dog = await dog_service.create_dog(current_user.uid, dog_data)
        return DogResponse(success=True, message="Dog created successfully", dog=dog)

    except Exception as e:
        logger.error(f"Error creating dog for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create dog")


@router.get(
    "/",
    summary="Get all dogs",
    description="Get all dogs owned by the authenticated user.",
    operation_id="dogs_list",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Unauthorized"}}},
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {"application/json": {"example": {"detail": "Failed to retrieve dogs"}}},
        },
        200: {
            "description": "Dogs retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Dogs retrieved successfully",
                        "dogs": [
                            {
                                "id": "dog-123",
                                "owner_uid": "user-123",
                                "name": "Buddy",
                                "breed": "Golden Retriever",
                                "age": 3,
                                "color": "Golden",
                                "weight_kg": 30.5,
                                "created_at": "2025-01-01T00:00:00Z",
                                "updated_at": "2025-01-01T00:00:00Z",
                            }
                        ],
                        "count": 1,
                    }
                }
            },
        },
    },
)
async def get_dogs(
    current_user: Annotated[FirebaseUser, Depends(_current_user_dependency)],
) -> DogListResponse:
    """
    Get all dogs owned by the authenticated user.

    Args:
        current_user: The authenticated Firebase user

    Returns:
        DogListResponse: The response with list of dogs

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        dogs = await dog_service.get_dogs_by_owner(current_user.uid)
        return DogListResponse(
            success=True,
            message="Dogs retrieved successfully",
            dogs=dogs,
            count=len(dogs),
        )

    except Exception as e:
        logger.error(f"Error retrieving dogs for user {current_user.uid}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve dogs")


@router.get(
    "/{dog_id}",
    summary="Get a dog",
    description="Get a specific dog by ID (must be owned by authenticated user).",
    operation_id="dog_get",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Unauthorized"}}},
        },
        404: {
            "model": ErrorResponse,
            "description": "Dog not found",
            "content": {"application/json": {"example": {"detail": "Dog not found"}}},
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to access this dog",
            "content": {"application/json": {"example": {"detail": "Not authorized to access this dog"}}},
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {"application/json": {"example": {"detail": "Failed to retrieve dog"}}},
        },
        200: {
            "description": "Dog retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Dog retrieved successfully",
                        "dog": {
                            "id": "dog-123",
                            "owner_uid": "user-123",
                            "name": "Buddy",
                            "breed": "Golden Retriever",
                            "age": 3,
                            "color": "Golden",
                            "weight_kg": 30.5,
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2025-01-01T00:00:00Z",
                        },
                    }
                }
            },
        },
    },
)
async def get_dog(
    dog_id: str,
    current_user: Annotated[FirebaseUser, Depends(_current_user_dependency)],
) -> DogResponse:
    """
    Get a specific dog by ID.

    Args:
        dog_id: The dog's unique identifier
        current_user: The authenticated Firebase user

    Returns:
        DogResponse: The response with dog data

    Raises:
        HTTPException: If dog not found or user not authorized
    """
    try:
        dog = await dog_service.get_dog(dog_id)

        if not dog:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dog not found")

        # Verify ownership
        if dog.owner_uid != current_user.uid:
            logger.warning(
                "Unauthorized dog access attempt",
                extra={"dog_id": dog_id, "requesting_user": current_user.uid, "owner": dog.owner_uid},
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this dog")

        return DogResponse(success=True, message="Dog retrieved successfully", dog=dog)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving dog {dog_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve dog")


@router.put(
    "/{dog_id}",
    summary="Update a dog",
    description="Update a dog's information (must be owned by authenticated user).",
    operation_id="dog_update",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Unauthorized"}}},
        },
        404: {
            "model": ErrorResponse,
            "description": "Dog not found",
            "content": {"application/json": {"example": {"detail": "Dog not found"}}},
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to update this dog",
            "content": {"application/json": {"example": {"detail": "Not authorized to update this dog"}}},
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {"application/json": {"example": {"detail": "Failed to update dog"}}},
        },
        200: {
            "description": "Dog updated",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Dog updated successfully",
                        "dog": {
                            "id": "dog-123",
                            "owner_uid": "user-123",
                            "name": "Buddy",
                            "breed": "Golden Retriever",
                            "age": 4,
                            "color": "Golden",
                            "weight_kg": 32.0,
                            "created_at": "2025-01-01T00:00:00Z",
                            "updated_at": "2025-01-02T00:00:00Z",
                        },
                    }
                }
            },
        },
    },
)
async def update_dog(
    dog_id: str,
    dog_data: DogUpdate,
    current_user: Annotated[FirebaseUser, Depends(_current_user_dependency)],
) -> DogResponse:
    """
    Update a dog's information.

    Args:
        dog_id: The dog's unique identifier
        dog_data: The dog data to update
        current_user: The authenticated Firebase user

    Returns:
        DogResponse: The response with updated dog

    Raises:
        HTTPException: If dog not found or user not authorized
    """
    try:
        dog = await dog_service.update_dog(dog_id, current_user.uid, dog_data)

        if not dog:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dog not found")

        return DogResponse(success=True, message="Dog updated successfully", dog=dog)

    except ValueError as e:
        logger.warning(f"Unauthorized dog update: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating dog {dog_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update dog")


@router.delete(
    "/{dog_id}",
    summary="Delete a dog",
    description="Delete a dog (must be owned by authenticated user).",
    operation_id="dog_delete",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized",
            "content": {"application/json": {"example": {"detail": "Unauthorized"}}},
        },
        404: {
            "model": ErrorResponse,
            "description": "Dog not found",
            "content": {"application/json": {"example": {"detail": "Dog not found"}}},
        },
        403: {
            "model": ErrorResponse,
            "description": "Not authorized to delete this dog",
            "content": {"application/json": {"example": {"detail": "Not authorized to delete this dog"}}},
        },
        500: {
            "model": ErrorResponse,
            "description": "Server error",
            "content": {"application/json": {"example": {"detail": "Failed to delete dog"}}},
        },
        200: {
            "description": "Dog deleted",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Dog deleted successfully",
                        "dog": None,
                    }
                }
            },
        },
    },
)
async def delete_dog(
    dog_id: str,
    current_user: Annotated[FirebaseUser, Depends(_current_user_dependency)],
) -> DogResponse:
    """
    Delete a dog.

    Args:
        dog_id: The dog's unique identifier
        current_user: The authenticated Firebase user

    Returns:
        DogResponse: The response confirming deletion

    Raises:
        HTTPException: If dog not found or user not authorized
    """
    try:
        deleted = await dog_service.delete_dog(dog_id, current_user.uid)

        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dog not found")

        return DogResponse(success=True, message="Dog deleted successfully", dog=None)

    except ValueError as e:
        logger.warning(f"Unauthorized dog deletion: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dog {dog_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete dog")
