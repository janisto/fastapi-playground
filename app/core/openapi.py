"""Generated OpenAPI 3.1 semantic projection for the portable API."""

from copy import deepcopy
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from app.core.problems import ERRORS
from app.models.error import ErrorSource, ProblemResponse, ValidationIssue
from app.models.hello import HelloCreate
from app.models.profile import ProfileCreate, ProfileUpdate
from app.models.types import SAFE_INTEGER_MAX

type OpenAPIResponse = dict[str, Any]

_HTTP_CREATED = 201
_HTTP_NO_CONTENT = 204
_HTTP_SUCCESS_BOUNDARY = 300
_HTTP_UNAUTHORIZED = 401
_HTTP_NOT_FOUND = 404
_HTTP_UNPROCESSABLE_CONTENT = 422
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVICE_UNAVAILABLE = 503
_BOUNDED_NAME_PATTERN = (
    r"^[^\u0000-\u001F\u007F-\u009F\u0020\u0085\u00A0\u1680\u2000-\u200A"
    r"\u2028\u2029\u202F\u205F\u3000]"
    r"(?:[^\u0000-\u001F\u007F-\u009F]{0,98}"
    r"[^\u0000-\u001F\u007F-\u009F\u0020\u0085\u00A0\u1680\u2000-\u200A"
    r"\u2028\u2029\u202F\u205F\u3000])?$"
)
_EMAIL_LOCAL_CHARACTERS = r"A-Za-z0-9!#$%&'*+/=?^_{|}~.-"
_EMAIL_LOCAL_EDGE_CHARACTERS = r"A-Za-z0-9!#$%&'*+/=?^_{|}~-"
_EMAIL_DOMAIN_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_CANONICAL_EMAIL_PATTERN = (
    rf"^(?![{_EMAIL_LOCAL_CHARACTERS}]*\.\.)(?:[{_EMAIL_LOCAL_EDGE_CHARACTERS}]|"
    rf"[{_EMAIL_LOCAL_EDGE_CHARACTERS}][{_EMAIL_LOCAL_CHARACTERS}]{{0,62}}"
    rf"[{_EMAIL_LOCAL_EDGE_CHARACTERS}])@{_EMAIL_DOMAIN_LABEL}(?:\.{_EMAIL_DOMAIN_LABEL})+$"
)
_INPUT_EMAIL_PATTERN = (
    r"^[\t-\r ]*(?=[^\t-\r ]{1,254}[\t-\r ]*$)"
    + _CANONICAL_EMAIL_PATTERN.removeprefix("^").removesuffix("$")
    + r"[\t-\r ]*$"
)
_INPUT_PHONE_PATTERN = r"^[\t-\r ]*\+[1-9][0-9]{6,14}[\t-\r ]*$"
_CANONICAL_PHONE_PATTERN = r"^\+[1-9][0-9]{6,14}$"
_REQUEST_ID_SCHEMA = {
    "type": "string",
    "minLength": 1,
    "maxLength": 128,
    "pattern": r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$",
}
_REQUEST_ID_PARAMETER = {
    "name": "X-Request-ID",
    "in": "header",
    "required": False,
    "description": (
        "Optional correlation identifier. Missing, invalid, repeated, or comma-combined values are replaced "
        "with a generated 32-character lowercase hexadecimal identifier."
    ),
    "schema": _REQUEST_ID_SCHEMA,
}
_COMMON_HEADERS = {
    "X-Request-ID": {"description": "Selected request correlation identifier.", "schema": _REQUEST_ID_SCHEMA},
    "Cache-Control": {"description": "Response caching policy.", "schema": {"type": "string", "const": "no-store"}},
    "X-Content-Type-Options": {
        "description": "MIME sniffing policy.",
        "schema": {"type": "string", "const": "nosniff"},
    },
    "X-Frame-Options": {"description": "Framing policy.", "schema": {"type": "string", "const": "DENY"}},
    "Referrer-Policy": {
        "description": "Referrer disclosure policy.",
        "schema": {"type": "string", "const": "strict-origin-when-cross-origin"},
    },
    "Vary": {"description": "Representation and optional origin variance.", "schema": {"type": "string"}},
}
_ERROR_STATUSES: dict[int, str] = {
    400: "Malformed request",
    401: "Authentication is required or invalid",
    404: "Resource not found",
    406: "No acceptable response representation",
    409: "Profile state conflict",
    413: "Request body is too large",
    415: "Request representation is unsupported",
    422: "Request validation failed",
    429: "GitHub rate limit exceeded",
    500: "Internal server error",
    502: "GitHub upstream response is invalid or unavailable",
    503: "A required dependency is unavailable",
    504: "GitHub request timed out",
}
_ERROR_CODES = {
    400: "invalid_request",
    401: "unauthorized",
    406: "not_acceptable",
    409: "profile_exists",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_failed",
    429: "github_rate_limit",
    500: "internal_error",
    502: "github_upstream",
    503: "dependency_unavailable",
    504: "github_timeout",
}
_STATUS_MAP: dict[tuple[str, str], tuple[int, ...]] = {
    ("get", "/health"): (200, 400, 406, 500),
    ("get", "/v1/hello"): (200, 400, 406, 500),
    ("post", "/v1/hello"): (200, 400, 406, 413, 415, 422, 500),
    ("get", "/v1/items"): (200, 400, 406, 422, 500),
    ("post", "/v1/profile"): (201, 400, 401, 406, 409, 413, 415, 422, 500, 503),
    ("get", "/v1/profile"): (200, 400, 401, 404, 406, 500, 503),
    ("patch", "/v1/profile"): (200, 400, 401, 404, 406, 413, 415, 422, 500, 503),
    ("delete", "/v1/profile"): (204, 400, 401, 404, 500, 503),
}
_GITHUB_PATHS = {
    "/v1/github/owners/{owner}",
    "/v1/github/owners/{owner}/repos",
    "/v1/github/repos/{owner}/{repo}",
    "/v1/github/repos/{owner}/{repo}/activity",
    "/v1/github/repos/{owner}/{repo}/languages",
    "/v1/github/repos/{owner}/{repo}/tags",
}
_PAGINATED_PATHS = {
    "/v1/items",
    "/v1/github/owners/{owner}/repos",
    "/v1/github/repos/{owner}/{repo}/activity",
    "/v1/github/repos/{owner}/{repo}/tags",
}


def _register_model(components: dict[str, Any], model: type[BaseModel]) -> None:
    schema = model.model_json_schema(ref_template="#/components/schemas/{model}", by_alias=True)
    definitions = schema.pop("$defs", {})
    components.update(definitions)
    components[model.__name__] = schema


def _error_response(status: int, *, profile: bool, github: bool = False) -> OpenAPIResponse:
    headers = deepcopy(_COMMON_HEADERS)
    if status == _HTTP_UNAUTHORIZED:
        headers["WWW-Authenticate"] = {
            "description": "Firebase bearer challenge.",
            "schema": {"type": "string", "const": "Bearer"},
        }
    if status == _HTTP_TOO_MANY_REQUESTS:
        headers["Retry-After"] = {
            "description": "Nonnegative seconds before another request.",
            "schema": {"type": "integer", "minimum": 0, "maximum": SAFE_INTEGER_MAX},
        }
        if github:
            headers["X-RateLimit-Reset"] = {
                "description": "Optional GitHub reset Unix timestamp.",
                "schema": {"type": "integer", "minimum": 0, "maximum": SAFE_INTEGER_MAX},
            }
    if status == _HTTP_SERVICE_UNAVAILABLE and profile:
        headers["Retry-After"] = {
            "description": "Present only when the failing dependency supplies a retry policy.",
            "schema": {"type": "integer", "minimum": 0, "maximum": SAFE_INTEGER_MAX},
        }
    code = (
        "github_not_found"
        if github and status == _HTTP_NOT_FOUND
        else "profile_not_found"
        if profile and status == _HTTP_NOT_FOUND
        else _ERROR_CODES[status]
    )
    definition = ERRORS[code]
    properties: dict[str, Any] = {
        "title": {"type": "string", "const": definition.title},
        "status": {"type": "integer", "const": status},
        "detail": {"type": "string", "const": definition.detail},
        "code": {"type": "string", "const": code},
    }
    if status == _HTTP_UNPROCESSABLE_CONTENT:
        properties["errors"] = {
            "type": "array",
            "minItems": 1,
            "maxItems": 32,
            "items": {"$ref": "#/components/schemas/ValidationIssue"},
        }
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "status", "detail", "code"],
        "properties": properties,
    }
    return {
        "description": _ERROR_STATUSES[status],
        "headers": headers,
        "content": {
            "application/problem+json": {"schema": schema},
            "application/cbor": {"schema": schema},
        },
    }


def _success_response(
    generated: dict[str, Any],
    status: int,
    *,
    path: str,
) -> OpenAPIResponse:
    original = generated.get(str(status), {})
    headers = deepcopy(_COMMON_HEADERS)
    if path in _PAGINATED_PATHS:
        headers["Link"] = {"description": "Optional RFC 8288 next and previous links.", "schema": {"type": "string"}}
    if path == "/v1/profile" and status == _HTTP_CREATED:
        headers["Location"] = {
            "description": "Canonical current-principal profile target.",
            "schema": {"type": "string", "const": "/v1/profile"},
        }
    response: OpenAPIResponse = {"description": original.get("description", "Successful response"), "headers": headers}
    if status != _HTTP_NO_CONTENT:
        original_content = original.get("content", {})
        json_schema = deepcopy(original_content.get("application/json", {}).get("schema", {}))
        response["content"] = {
            "application/json": {"schema": json_schema},
            "application/cbor": {"schema": deepcopy(json_schema)},
        }
    return response


def _item_parameters() -> list[dict[str, Any]]:
    return [
        {
            "name": "limit",
            "in": "query",
            "required": False,
            "description": "Closed query; repeated and unknown parameters are rejected.",
            "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
        },
        {
            "name": "cursor",
            "in": "query",
            "required": False,
            "description": "Opaque, operation-, limit-, filter-, direction-, and position-scoped cursor.",
            "schema": {"type": "string", "minLength": 1, "maxLength": 2048, "pattern": r"^[!-~]+$"},
        },
        {
            "name": "category",
            "in": "query",
            "required": False,
            "description": "Optional exact catalog category filter.",
            "schema": {
                "type": "string",
                "enum": ["electronics", "tools", "accessories", "robotics", "power", "components"],
            },
        },
    ]


def _tighten_component_schemas(components: dict[str, Any]) -> None:
    for component_name, property_name in (
        ("HelloCreate", "name"),
        ("Item", "name"),
        ("ProfileCreate", "firstName"),
        ("ProfileCreate", "lastName"),
        ("ProfileUpdate", "firstName"),
        ("ProfileUpdate", "lastName"),
        ("Profile", "firstName"),
        ("Profile", "lastName"),
    ):
        components[component_name]["properties"][property_name]["pattern"] = _BOUNDED_NAME_PATTERN

    for component_name in ("ProfileCreate", "ProfileUpdate"):
        email = components[component_name]["properties"]["contactEmail"]
        email.pop("maxLength", None)
        email.update(
            {
                "pattern": _INPUT_EMAIL_PATTERN,
                "description": "ASCII email; surrounding ASCII whitespace is stripped and the domain is lowercased.",
            }
        )
        components[component_name]["properties"]["phoneNumber"].update(
            {
                "pattern": _INPUT_PHONE_PATTERN,
                "description": "E.164 phone number after stripping surrounding ASCII whitespace.",
            }
        )

    profile_properties = components["Profile"]["properties"]
    profile_properties["contactEmail"].update({"pattern": _CANONICAL_EMAIL_PATTERN, "maxLength": 254})
    profile_properties["phoneNumber"]["pattern"] = _CANONICAL_PHONE_PATTERN


def build_openapi_document(app: FastAPI) -> dict[str, Any]:  # noqa: C901, PLR0912
    """Generate and cache the semantic contract from the registered routes."""
    if app.openapi_schema is not None:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        openapi_version="3.1.0",
    )
    schema["jsonSchemaDialect"] = "https://json-schema.org/draft/2020-12/schema"
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    for model in (ErrorSource, ValidationIssue, ProblemResponse, HelloCreate, ProfileCreate, ProfileUpdate):
        _register_model(components, model)
    components["ErrorSource"] = {
        "oneOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": [name],
                "properties": {name: {"type": "string", "minLength": 1, "maxLength": 256}},
            }
            for name in ("pointer", "parameter", "header")
        ]
    }
    components["ValidationIssue"] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["detail"],
        "properties": {
            "detail": {"type": "string", "minLength": 1, "maxLength": 200},
            "source": {"$ref": "#/components/schemas/ErrorSource"},
        },
    }
    components["ProblemResponse"] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "status", "detail", "code"],
        "properties": {
            "title": {"type": "string"},
            "status": {"type": "integer"},
            "detail": {"type": "string"},
            "code": {"type": "string", "enum": sorted(ERRORS)},
            "errors": {
                "type": "array",
                "minItems": 1,
                "maxItems": 32,
                "items": {"$ref": "#/components/schemas/ValidationIssue"},
            },
        },
    }
    _tighten_component_schemas(components)
    schema["components"]["securitySchemes"] = {
        "FirebaseBearer": {
            "type": "http",
            "scheme": "bearer",
            "description": "Firebase ID token; the verified subject selects the current-principal profile.",
        }
    }

    for path, path_item in schema["paths"].items():
        for method, operation in path_item.items():
            if method not in {"get", "post", "patch", "delete"}:
                continue
            profile = path == "/v1/profile"
            github = path in _GITHUB_PATHS
            operation["security"] = [{"FirebaseBearer": []}] if profile else []
            parameters = operation.setdefault("parameters", [])
            parameters.append(deepcopy(_REQUEST_ID_PARAMETER))
            if path == "/v1/items":
                operation["parameters"] = [*_item_parameters(), deepcopy(_REQUEST_ID_PARAMETER)]
            for parameter in operation["parameters"]:
                if parameter.get("in") == "query":
                    parameter_schema = parameter.get("schema", {})
                    if isinstance(parameter_schema, dict) and "anyOf" in parameter_schema:
                        non_null = [entry for entry in parameter_schema["anyOf"] if entry.get("type") != "null"]
                        if len(non_null) == 1:
                            parameter["schema"] = non_null[0]
                    parameter["description"] = (
                        str(parameter.get("description", ""))
                        + " The query is closed; unknown and repeated parameters are rejected."
                    ).strip()
                if parameter.get("name") == "repo":
                    parameter["schema"]["pattern"] = r"^(?=.*[A-Za-z0-9_-])[A-Za-z0-9._-]+$"
                if parameter.get("name") == "cursor":
                    parameter["schema"]["pattern"] = r"^[!-~]+$"

            statuses = (200, 400, 404, 406, 422, 429, 500, 502, 504) if github else _STATUS_MAP[(method, path)]
            generated_responses = operation.get("responses", {})
            responses: dict[str, Any] = {}
            for status in statuses:
                if status < _HTTP_SUCCESS_BOUNDARY:
                    responses[str(status)] = _success_response(generated_responses, status, path=path)
                else:
                    responses[str(status)] = _error_response(status, profile=profile, github=github)
            operation["responses"] = responses

    app.openapi_schema = schema
    return schema
