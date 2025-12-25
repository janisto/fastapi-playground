---
name: domain-exception
description: Guide for creating domain exceptions with HTTP semantics that are automatically converted to HTTP responses by exception handlers.
---
# Domain Exception Creation

Use this skill when creating domain exceptions that carry HTTP semantics for automatic response conversion.

For comprehensive coding guidelines, see `AGENTS.md` in the repository root.

## Base Exception Classes

The project has these base classes in `app/exceptions/base.py`:

```python
class DomainError(Exception):
    """
    Base for all domain exceptions with HTTP semantics.

    Supports optional headers for cases like rate limiting (Retry-After).
    """

    status_code: int = 500
    detail: str = "Internal error"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str | None = None, headers: dict[str, str] | None = None) -> None:
        self.detail = detail or self.__class__.detail
        self.headers = headers
        super().__init__(self.detail)


class NotFoundError(DomainError):
    """
    Base for resource not found errors.
    """

    status_code = 404
    detail = "Resource not found"


class ConflictError(DomainError):
    """
    Base for resource conflict errors.
    """

    status_code = 409
    detail = "Resource conflict"
```

## Creating Resource-Specific Exceptions

Create new exceptions in `app/exceptions/`:

```python
# app/exceptions/resource.py
"""
Resource-related exceptions.
"""

from app.exceptions.base import ConflictError, NotFoundError


class ResourceNotFoundError(NotFoundError):
    """
    Raised when a resource cannot be found.
    """

    detail = "Resource not found"


class ResourceAlreadyExistsError(ConflictError):
    """
    Raised when attempting to create a duplicate resource.
    """

    detail = "Resource already exists"
```

## Exporting Exceptions

Export new exceptions from `app/exceptions/__init__.py`:

```python
from app.exceptions.base import ConflictError, DomainError, NotFoundError
from app.exceptions.resource import ResourceAlreadyExistsError, ResourceNotFoundError

__all__ = [
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "ResourceAlreadyExistsError",
    "ResourceNotFoundError",
]
```

## Using Exceptions

Import from the package root:

```python
# In routers and services
from app.exceptions import ResourceNotFoundError, ResourceAlreadyExistsError
```

Raise exceptions in services:

```python
async def get_resource(self, user_id: str) -> Resource:
    snapshot = await doc_ref.get()
    if not snapshot.exists:
        raise ResourceNotFoundError("Resource not found")
    return Resource(**snapshot.to_dict())
```

## Exception Handling in Routers

Re-raise domain exceptions to let handlers convert them:

```python
@router.get("/")
async def get_resource(
    current_user: CurrentUser,
    service: ResourceServiceDep,
) -> ResourceResponse:
    try:
        resource = await service.get_resource(current_user.uid)
        return ResourceResponse(success=True, message="Resource retrieved", resource=resource)
    except (HTTPException, ResourceNotFoundError):
        raise
    except Exception:
        logger.exception("Error getting resource", extra={"user_id": current_user.uid})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve resource"
        ) from None
```

## Custom Headers

Use headers for cases like rate limiting:

```python
class RateLimitExceededError(DomainError):
    """
    Raised when rate limit is exceeded.
    """

    status_code = 429
    detail = "Rate limit exceeded"


# Usage with Retry-After header
raise RateLimitExceededError(
    detail="Too many requests",
    headers={"Retry-After": "60"}
)
```

## Common Exception Types

| Base Class | Status Code | Use Case |
|------------|-------------|----------|
| `DomainError` | 500 | Generic internal errors |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Duplicate resource, state conflict |

## Exception Handler

The domain exception handler in `app/core/handlers/domain.py` automatically converts exceptions:

```python
async def domain_exception_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )
```

## Naming Convention

Use descriptive names with `Error` suffix:
- `{Resource}NotFoundError`
- `{Resource}AlreadyExistsError`
- `{Resource}InvalidError`
- `{Resource}ExpiredError`

## Testing

Test exception behavior:

```python
def test_returns_404_when_not_found(
    client: TestClient,
    with_fake_user: None,
    mock_resource_service: AsyncMock,
) -> None:
    mock_resource_service.get_resource.side_effect = ResourceNotFoundError()

    response = client.get("/resource/")

    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found"
```
