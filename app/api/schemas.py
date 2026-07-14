"""
JSON Schema discovery routes.

Serves JSON Schemas for API response types extracted from OpenAPI spec.
Enables clients to discover and validate response structures.

See: https://json-schema.org/draft/2020-12/json-schema-core.html
"""

from copy import deepcopy
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.cbor import NotAcceptableHTTPException
from app.core.content_negotiation import SCHEMA_JSON_MEDIA_TYPE, negotiate_media_type
from app.exceptions import SchemaNotFoundError

router = APIRouter(prefix="/schemas", tags=["Schemas"])

_OPENAPI_COMPONENT_PREFIX = "#/components/schemas/"
_JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"

type JSONValue = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]

_schema_cache: dict[str, dict[str, Any]] = {}


def _rewrite_component_refs(value: JSONValue, referenced: set[str]) -> None:
    """
    Rewrite OpenAPI component references for a standalone JSON Schema.
    """
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith(_OPENAPI_COMPONENT_PREFIX):
            schema_name = ref.removeprefix(_OPENAPI_COMPONENT_PREFIX)
            referenced.add(schema_name)
            value["$ref"] = f"#/$defs/{schema_name}"
        for child in value.values():
            _rewrite_component_refs(child, referenced)
    elif isinstance(value, list):
        for child in value:
            _rewrite_component_refs(child, referenced)


def _build_standalone_schema(
    schema_name: str,
    components: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a self-contained JSON Schema from an OpenAPI component.
    """
    schema = deepcopy(components[schema_name])
    referenced: set[str] = set()
    _rewrite_component_refs(schema, referenced)

    definitions: dict[str, dict[str, Any]] = {}
    while referenced:
        referenced_name = referenced.pop()
        if referenced_name in definitions:
            continue
        definition = deepcopy(components[referenced_name])
        definitions[referenced_name] = definition
        _rewrite_component_refs(definition, referenced)

    schema["$schema"] = _JSON_SCHEMA_DIALECT
    if definitions:
        schema["$defs"] = definitions
    return schema


def populate_schema_cache(openapi_schema: dict[str, Any]) -> None:
    """
    Populate schema cache from OpenAPI spec.

    Called during application startup to extract JSON schemas from
    the OpenAPI components.schemas section.
    """
    schemas: dict[str, dict[str, Any]] = openapi_schema.get("components", {}).get("schemas", {})
    _schema_cache.clear()
    _schema_cache.update({name: _build_standalone_schema(name, schemas) for name in schemas})


@router.get(
    "/{schema_name}",
    include_in_schema=False,
    response_class=JSONResponse,
)
async def get_schema(schema_name: str, request: Request) -> JSONResponse:
    """
    Retrieve a JSON Schema by name.

    Returns the JSON Schema for the specified model from the API's
    OpenAPI specification. Schema names correspond to Pydantic model
    class names (e.g., HealthResponse, Greeting, ItemList).

    The .json extension is optional and will be stripped if present.
    """
    accept = ",".join(request.headers.getlist("accept"))
    if (
        negotiate_media_type(
            accept,
            (SCHEMA_JSON_MEDIA_TYPE,),
            default=SCHEMA_JSON_MEDIA_TYPE,
        )
        is None
    ):
        raise NotAcceptableHTTPException(SCHEMA_JSON_MEDIA_TYPE)

    name = schema_name.removesuffix(".json")
    if name not in _schema_cache:
        raise SchemaNotFoundError(detail=f"Schema '{name}' not found")

    return JSONResponse(
        content=_schema_cache[name],
        media_type=SCHEMA_JSON_MEDIA_TYPE,
    )
