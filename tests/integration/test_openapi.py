"""
Integration tests for the generated OpenAPI contract.
"""

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
