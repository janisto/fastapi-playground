---
name: fastapi-endpoint
description: Guide for creating FastAPI endpoints following this project's conventions including routers, dependency injection, error handling, and OpenAPI documentation.
---
# FastAPI Endpoint Creation

Use this skill when creating new API endpoints for this FastAPI application. Follow these patterns to ensure consistency with the existing codebase.

## Router Setup

Create routers in `app/routers/` with proper configuration:

```python
"""
Resource router for resource management.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, ResourceServiceDep
from app.exceptions import ResourceNotFoundError, ResourceAlreadyExistsError
from app.models.error import ErrorResponse
from app.models.resource import ResourceCreate, ResourceResponse, ResourceUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/resource",
    tags=["Resource"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
```

## Endpoint Pattern

Always include:
- `status_code` for non-200 responses
- `response_model` or return type annotation
- `summary` and `description` for OpenAPI docs
- `operation_id` with pattern `<resource>_<action>`
- `responses` dict for all possible status codes

```python
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ResourceResponse,
    summary="Create resource",
    description="Create a new resource for the authenticated user.",
    operation_id="resource_create",
    responses={
        201: {"model": ResourceResponse, "description": "Resource created successfully"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        409: {"model": ErrorResponse, "description": "Resource already exists"},
    },
)
async def create_resource(
    resource_data: ResourceCreate,
    current_user: CurrentUser,
    service: ResourceServiceDep,
) -> ResourceResponse:
    """
    Create a new resource for the authenticated user.

    Stores the resource data in Firestore under the user's UID.
    Returns 409 Conflict if a resource already exists.
    """
    try:
        resource = await service.create_resource(current_user.uid, resource_data)
        return ResourceResponse(success=True, message="Resource created successfully", resource=resource)
    except (HTTPException, ResourceAlreadyExistsError):
        raise
    except Exception:
        logger.exception("Error creating resource", extra={"user_id": current_user.uid})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create resource"
        ) from None
```

## Dependencies

Use typed dependency aliases from `app/dependencies.py`:
- `CurrentUser` for authenticated user context
- Service dependencies like `ResourceServiceDep`

Create new service dependencies in `app/dependencies.py`:

```python
from app.services.resource import ResourceService

def get_resource_service() -> ResourceService:
    """
    Dependency provider for ResourceService.
    """
    return ResourceService()

ResourceServiceDep = Annotated[ResourceService, Depends(get_resource_service)]
```

## Error Handling

- Re-raise domain exceptions and `HTTPException` to let handlers convert them
- Use `logger.exception()` with structured `extra={}` for unexpected errors
- Use `from None` to suppress exception chaining in generic 500 responses
- Never expose internal error details to clients

## PATCH Endpoints

For partial updates, use `response_model_exclude_unset=True`:

```python
@router.patch(
    "/",
    response_model=ResourceResponse,
    response_model_exclude_unset=True,
    operation_id="resource_update",
    ...
)
```

## Router Registration

Register new routers in `app/main.py`:

```python
from app.routers import resource

app.include_router(resource.router)
```

## URL Conventions

- Always use trailing slashes (e.g., `/resource/` not `/resource`)
- Use plural nouns for collection endpoints
- Keep routes RESTful: POST for create, GET for read, PATCH for update, DELETE for delete
