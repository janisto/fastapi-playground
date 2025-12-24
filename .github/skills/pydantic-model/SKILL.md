---
name: pydantic-model
description: Guide for creating Pydantic v2 models with proper validation, field examples, and schema separation following this project's conventions.
---
# Pydantic Model Creation

Use this skill when creating Pydantic models for request/response schemas in this FastAPI application.

## Model File Structure

Create models in `app/models/` with a docstring explaining the module and any constants:

```python
"""
Resource data models.

Constants
---------
`RESOURCE_COLLECTION` is the canonical Firestore collection name for resource documents.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.types import NormalizedEmail, Phone

# Firestore collection name
RESOURCE_COLLECTION = "resources"
```

## Request Models (Base and Create)

Use `extra="forbid"` for request models to reject unknown fields:

```python
class ResourceBase(BaseModel):
    """
    Base resource model with common fields.
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Resource name",
        examples=["My Resource"],
    )
    email: NormalizedEmail = Field(
        ...,
        description="Email address (auto-lowercased)",
        examples=["user@example.com"],
    )
    active: bool = Field(
        default=True,
        description="Whether the resource is active",
        examples=[True],
    )

    model_config = ConfigDict(extra="forbid")


class ResourceCreate(ResourceBase):
    """
    Model for creating a new resource.
    """
```

## Update Models

Make all fields optional for partial updates:

```python
class ResourceUpdate(BaseModel):
    """
    Model for updating an existing resource.
    """

    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Resource name",
        examples=["Updated Resource"],
    )
    active: bool | None = Field(
        None,
        description="Whether the resource is active",
        examples=[False],
    )

    model_config = ConfigDict(extra="forbid")
```

## Entity Models (Response)

Response models should NOT inherit from request base models with `extra="forbid"`:

```python
class Resource(BaseModel):
    """
    Complete resource model with metadata.

    Note: Does not inherit from ResourceBase to avoid extra="forbid" which is
    inappropriate for response models.
    """

    id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Unique identifier",
        examples=["resource-abc123"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Resource name",
        examples=["My Resource"],
    )
    active: bool = Field(
        default=True,
        description="Whether the resource is active",
        examples=[True],
    )
    created_at: datetime = Field(
        ...,
        description="Creation timestamp",
        examples=["2025-01-15T10:30:00Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="Last update timestamp",
        examples=["2025-01-15T10:30:00Z"],
    )
```

## Response Wrapper Models

Wrap entity models in response models:

```python
class ResourceResponse(BaseModel):
    """
    Response model for resource operations.
    """

    success: bool = Field(..., description="Operation success status", examples=[True])
    message: str = Field(..., description="Result message", examples=["Resource created successfully"])
    resource: Resource | None = Field(None, description="Resource data if available")
```

## Field Requirements

Every field MUST have:
- `Field(...)` with `description` for OpenAPI documentation
- `examples=[...]` for per-field examples in Swagger/ReDoc

Example formats by type:
| Field Type | Example Format |
|------------|----------------|
| `str` | `examples=["value"]` |
| `int` | `examples=[123]` |
| `float` | `examples=[19.99]` |
| `bool` | `examples=[True]` |
| `datetime` | `examples=["2025-01-15T10:30:00Z"]` |
| `list[str]` | `examples=[["item1", "item2"]]` |
| `EmailStr` | `examples=["user@example.com"]` |
| `T \| None` | Provide example for `T`; omit `None` |

## Shared Type Aliases

Use predefined types from `app/models/types.py`:
- `NormalizedEmail` for auto-lowercased emails
- `Phone` for E.164 phone numbers
- `LanguageCode` for ISO 639-1 codes
- `CountryCode` for ISO 3166-1 alpha-2 codes

## Naming Conventions

| Purpose | Pattern | Example |
|---------|---------|---------|
| Base class (internal) | `{Resource}Base` | `ProfileBase` |
| Create request | `{Resource}Create` | `ProfileCreate` |
| Update request | `{Resource}Update` | `ProfileUpdate` |
| Full entity | `{Resource}` | `Profile` |
| Response wrapper | `{Resource}Response` | `ProfileResponse` |

## Serialization

Use Pydantic v2 methods:
- `.model_dump()` instead of deprecated `.dict()`
- `.model_dump(exclude_unset=True)` for partial updates
- `.model_validate()` instead of deprecated `.parse_obj()`
