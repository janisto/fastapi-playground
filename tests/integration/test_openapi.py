"""
Integration tests for the generated OpenAPI contract.
"""

from typing import cast

from app.main import fastapi_app

EXPECTED_OPERATIONS = {
    ("get", "/health", "health_get"),
    ("get", "/v1/hello", "hello_get"),
    ("post", "/v1/hello", "hello_create"),
    ("get", "/v1/items", "items_list"),
    ("post", "/v1/profile", "profile_create"),
    ("get", "/v1/profile", "profile_get"),
    ("patch", "/v1/profile", "profile_update"),
    ("delete", "/v1/profile", "profile_delete"),
}


def test_exact_operation_set_and_unique_ids() -> None:
    """
    Verify the generated contract matches route registration exactly.
    """
    schema = fastapi_app.openapi()
    operations = {
        (method, path, operation["operationId"])
        for path, path_item in schema["paths"].items()
        for method, operation in path_item.items()
    }

    assert operations == EXPECTED_OPERATIONS
    operation_ids = [operation_id for _method, _path, operation_id in operations]
    assert len(operation_ids) == len(set(operation_ids))


def test_only_profile_operations_require_bearer_authentication() -> None:
    """
    Verify bearer security matches the protected route boundary.
    """
    schema = fastapi_app.openapi()
    for path, path_item in schema["paths"].items():
        for operation in path_item.values():
            if path == "/v1/profile":
                assert operation["security"] == [{"HTTPBearer": []}]
            else:
                assert "security" not in operation


def test_profile_operations_document_authentication_unavailability() -> None:
    """
    Verify protected operations document the authentication dependency failure.
    """
    profile_operations = fastapi_app.openapi()["paths"]["/v1/profile"].values()

    for operation in profile_operations:
        assert operation["responses"]["503"]["description"] == "Authentication service unavailable"


def test_cbor_routes_document_success_and_problem_representations() -> None:
    """
    Verify the contract advertises each representation implemented at runtime.
    """
    schema = fastapi_app.openapi()
    for path, method in [
        ("/v1/hello", "get"),
        ("/v1/hello", "post"),
        ("/v1/items", "get"),
        ("/v1/profile", "get"),
        ("/v1/profile", "post"),
        ("/v1/profile", "patch"),
    ]:
        operation = schema["paths"][path][method]
        success_status = "201" if method == "post" else "200"
        assert set(operation["responses"][success_status]["content"]) == {
            "application/json",
            "application/cbor",
        }
        assert set(operation["responses"]["406"]["content"]) == {
            "application/problem+json",
            "application/problem+cbor",
        }


def test_health_contract_remains_json_only() -> None:
    """
    Verify the liveness endpoint does not advertise unsupported CBOR success responses.
    """
    responses = fastapi_app.openapi()["paths"]["/health"]["get"]["responses"]

    assert set(responses["200"]["content"]) == {"application/json"}
    assert set(responses["406"]["content"]) == {
        "application/problem+json",
        "application/problem+cbor",
    }


def test_profile_update_schema_rejects_null_without_requiring_fields() -> None:
    """
    Verify PATCH fields are omissible but are not documented as nullable.
    """
    schema = fastapi_app.openapi()["components"]["schemas"]["ProfileUpdate"]

    assert "required" not in schema
    for field_schema in schema["properties"].values():
        assert field_schema.get("type") != "null"
        assert {variant.get("type") for variant in field_schema.get("anyOf", [])} <= {"string", "boolean"}


def test_response_headers_match_runtime_contract() -> None:
    """
    Verify request correlation, discovery, authentication, and creation headers are documented.
    """
    schema = fastapi_app.openapi()
    profile = schema["paths"]["/v1/profile"]

    assert set(profile["post"]["responses"]["201"]["headers"]) == {
        "X-Request-ID",
        "Link",
        "Location",
    }
    assert "WWW-Authenticate" in profile["get"]["responses"]["401"]["headers"]
    assert "Retry-After" in profile["get"]["responses"]["503"]["headers"]
    assert set(profile["delete"]["responses"]["204"]["headers"]) == {"X-Request-ID"}


def test_exact_route_specific_error_statuses_are_documented() -> None:
    """
    Verify known business and transport failures are explicit in the contract.
    """
    schema = fastapi_app.openapi()["paths"]

    assert "400" in schema["/v1/items"]["get"]["responses"]
    assert "409" in schema["/v1/profile"]["post"]["responses"]
    assert "404" in schema["/v1/profile"]["get"]["responses"]
    for path in ("/v1/hello", "/v1/items", "/v1/profile"):
        for operation in schema[path].values():
            assert {"400", "406", "413", "415", "500"} <= set(operation["responses"])

    assert "422" not in schema["/v1/hello"]["get"]["responses"]
    assert "422" in schema["/v1/hello"]["post"]["responses"]
    assert "422" in schema["/v1/items"]["get"]["responses"]
    assert "422" not in schema["/v1/profile"]["get"]["responses"]
    assert "422" not in schema["/v1/profile"]["delete"]["responses"]
    assert "422" in schema["/v1/profile"]["post"]["responses"]
    assert "422" in schema["/v1/profile"]["patch"]["responses"]


def test_all_local_schema_references_resolve() -> None:
    """
    Verify generated response schemas do not retain Pydantic-local references.
    """
    schema = fastapi_app.openapi()

    def collect_refs(value: object) -> list[str]:
        if isinstance(value, dict):
            mapping = cast("dict[str, object]", value)
            ref_value = mapping.get("$ref")
            refs = [ref_value] if isinstance(ref_value, str) else []
            return refs + [ref for child in mapping.values() for ref in collect_refs(child)]
        if isinstance(value, list):
            return [ref for child in cast("list[object]", value) for ref in collect_refs(child)]
        return []

    refs = collect_refs(schema)
    assert refs
    for ref in refs:
        assert ref.startswith("#/components/schemas/")
        assert ref.removeprefix("#/components/schemas/") in schema["components"]["schemas"]
