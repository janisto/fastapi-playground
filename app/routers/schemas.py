"""
JSON Schema discovery routes.

Serves JSON Schemas for API response types extracted from OpenAPI spec.
Enables clients to discover and validate response structures.

See: https://json-schema.org/draft/2020-12/json-schema-core.html
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.exceptions import SchemaNotFoundError

router = APIRouter(prefix="/schemas", tags=["Schemas"])

_schema_cache: dict[str, dict] = {}


def populate_schema_cache(openapi_schema: dict) -> None:
    """
    Populate schema cache from OpenAPI spec.

    Called during application startup to extract JSON schemas from
    the OpenAPI components.schemas section.
    """
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    _schema_cache.clear()
    _schema_cache.update(schemas)


@router.get(
    "/{schema_name}",
    include_in_schema=False,
    response_class=JSONResponse,
)
async def get_schema(schema_name: str) -> JSONResponse:
    """
    Retrieve a JSON Schema by name.

    Returns the JSON Schema for the specified model from the API's
    OpenAPI specification. Schema names correspond to Pydantic model
    class names (e.g., HealthResponse, Greeting, ItemList).

    The .json extension is optional and will be stripped if present.
    """
    name = schema_name.removesuffix(".json")

    if name not in _schema_cache:
        raise SchemaNotFoundError(detail=f"Schema '{name}' not found")

    return JSONResponse(
        content=_schema_cache[name],
        media_type="application/schema+json",
    )
