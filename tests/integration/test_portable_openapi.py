"""Semantic OpenAPI/runtime agreement tests for the portable GCP profile."""

import re
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock

import cbor2
import pytest
from fastapi.testclient import TestClient

from app.auth.firebase import verify_firebase_token

EXPECTED_OPERATIONS = {
    ("get", "/health"): "getHealth",
    ("get", "/v1/hello"): "getHello",
    ("post", "/v1/hello"): "createHello",
    ("get", "/v1/items"): "listItems",
    ("post", "/v1/profile"): "createProfile",
    ("get", "/v1/profile"): "getProfile",
    ("patch", "/v1/profile"): "updateProfile",
    ("delete", "/v1/profile"): "deleteProfile",
    ("get", "/v1/github/owners/{owner}"): "getGitHubOwner",
    ("get", "/v1/github/owners/{owner}/repos"): "listGitHubOwnerRepositories",
    ("get", "/v1/github/repos/{owner}/{repo}"): "getGitHubRepository",
    ("get", "/v1/github/repos/{owner}/{repo}/activity"): "listGitHubRepositoryActivity",
    ("get", "/v1/github/repos/{owner}/{repo}/languages"): "listGitHubRepositoryLanguages",
    ("get", "/v1/github/repos/{owner}/{repo}/tags"): "listGitHubRepositoryTags",
}
EXPECTED_STATUSES = {
    ("get", "/health"): {200, 400, 406, 500},
    ("get", "/v1/hello"): {200, 400, 406, 500},
    ("post", "/v1/hello"): {200, 400, 406, 413, 415, 422, 500},
    ("get", "/v1/items"): {200, 400, 406, 422, 500},
    ("post", "/v1/profile"): {201, 400, 401, 406, 409, 413, 415, 422, 500, 503},
    ("get", "/v1/profile"): {200, 400, 401, 404, 406, 500, 503},
    ("patch", "/v1/profile"): {200, 400, 401, 404, 406, 413, 415, 422, 500, 503},
    ("delete", "/v1/profile"): {204, 400, 401, 404, 500, 503},
}
COMMON_HEADERS = {
    "X-Request-ID",
    "Cache-Control",
    "Content-Security-Policy",
    "Cross-Origin-Opener-Policy",
    "Cross-Origin-Resource-Policy",
    "Permissions-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
    "Strict-Transport-Security",
    "Vary",
}
SECURITY_HEADER_VALUES = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Permissions-Policy": (
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def _operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (method, path): operation
        for path, path_item in document["paths"].items()
        for method, operation in path_item.items()
        if method in {"get", "post", "patch", "delete"}
    }


def _references(value: Any) -> Iterator[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "$ref":
                yield child
            else:
                yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _resolve(document: dict[str, Any], reference: str) -> Any:
    assert reference.startswith("#/")
    value: Any = document
    for token in reference[2:].split("/"):
        value = value[token.replace("~1", "/").replace("~0", "~")]
    return value


def test_runtime_openapi_inventory_security_and_statuses_are_exact(client: TestClient) -> None:
    response = client.get("/openapi.json", headers={"Accept": "application/json"})
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["Cache-Control"] == "no-store"
    document = response.json()
    assert document["openapi"].startswith("3.1.")
    assert document["jsonSchemaDialect"] == "https://json-schema.org/draft/2020-12/schema"

    operations = _operations(document)
    assert {(key, operation["operationId"]) for key, operation in operations.items()} == set(
        EXPECTED_OPERATIONS.items()
    )
    assert "/openapi.json" not in document["paths"]
    assert len({operation["operationId"] for operation in operations.values()}) == 14

    for key, operation in operations.items():
        assert operation["security"] == ([{"FirebaseBearer": []}] if key[1] == "/v1/profile" else [])
        request_id = [parameter for parameter in operation["parameters"] if parameter["name"] == "X-Request-ID"]
        assert len(request_id) == 1
        assert request_id[0]["required"] is False
        assert request_id[0]["schema"]["maxLength"] == 128
        expected_statuses = (
            {200, 400, 404, 406, 422, 429, 500, 502, 504} if "/github/" in key[1] else EXPECTED_STATUSES[key]
        )
        assert {int(status) for status in operation["responses"]} == expected_statuses
        for status, response_object in operation["responses"].items():
            assert set(response_object["headers"]) >= COMMON_HEADERS, (key, status)
            for header, value in SECURITY_HEADER_VALUES.items():
                assert response_object["headers"][header]["schema"]["const"] == value
            if int(status) < 300 and int(status) != 204:
                assert set(response_object["content"]) == {"application/json", "application/cbor"}
            elif int(status) >= 300:
                assert set(response_object["content"]) == {"application/problem+json", "application/cbor"}
                for media in response_object["content"].values():
                    schema = media["schema"]
                    assert schema["properties"]["status"]["const"] == int(status)
                    assert schema["properties"]["code"]["const"]

    scheme = document["components"]["securitySchemes"]["FirebaseBearer"]
    assert scheme["type"] == "http"
    assert scheme["scheme"] == "bearer"
    assert "Firebase" in scheme["description"]


def test_documented_security_headers_match_runtime_and_describe_conditional_hsts(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    headers = document["paths"]["/health"]["get"]["responses"]["200"]["headers"]
    response = client.get("/health")

    for header, value in SECURITY_HEADER_VALUES.items():
        assert headers[header]["schema"]["const"] == value
        if header == "Strict-Transport-Security":
            assert header not in response.headers
            assert "production HTTPS" in headers[header]["description"]
        else:
            assert response.headers[header] == value


def test_documented_422_responses_require_runtime_validation_issues(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    operations = _operations(document)

    for key, operation in operations.items():
        response = operation["responses"].get("422")
        if response is None:
            continue
        for media in response["content"].values():
            assert "errors" in media["schema"]["required"], key


def test_request_bodies_parameters_media_and_special_headers_are_exact(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    operations = _operations(document)
    body_operations = {
        ("post", "/v1/hello"): "HelloCreate",
        ("post", "/v1/profile"): "ProfileCreate",
        ("patch", "/v1/profile"): "ProfileUpdate",
    }
    for key, operation in operations.items():
        if key in body_operations:
            assert operation["requestBody"]["required"] is True
            assert set(operation["requestBody"]["content"]) == {"application/json", "application/cbor"}
            for media in operation["requestBody"]["content"].values():
                assert media["schema"] == {"$ref": f"#/components/schemas/{body_operations[key]}"}
        else:
            assert "requestBody" not in operation

    items = operations[("get", "/v1/items")]
    parameters = {parameter["name"]: parameter for parameter in items["parameters"]}
    assert set(parameters) == {"limit", "cursor", "category", "X-Request-ID"}
    assert parameters["limit"]["schema"] == {
        "type": "integer",
        "minimum": 1,
        "maximum": 100,
        "default": 20,
    }
    assert parameters["category"]["schema"]["enum"] == [
        "electronics",
        "tools",
        "accessories",
        "robotics",
        "power",
        "components",
    ]
    assert "Link" in items["responses"]["200"]["headers"]
    assert "Location" in operations[("post", "/v1/profile")]["responses"]["201"]["headers"]
    assert "WWW-Authenticate" in operations[("get", "/v1/profile")]["responses"]["401"]["headers"]
    quota = operations[("get", "/v1/github/owners/{owner}")]["responses"]["429"]["headers"]
    assert quota["Retry-After"]["schema"]["maximum"] == 9_007_199_254_740_991
    assert quota["X-RateLimit-Reset"]["schema"]["maximum"] == 9_007_199_254_740_991


def test_reachable_component_schemas_are_closed_and_constrained(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    components = document["components"]["schemas"]
    for name in (
        "HealthResponse",
        "HelloCreate",
        "Greeting",
        "Money",
        "Item",
        "ItemPage",
        "ProfileCreate",
        "ProfileUpdate",
        "Profile",
        "GitHubOwner",
        "GitHubRepository",
        "GitHubRepositoryPage",
        "GitHubActivity",
        "GitHubActivityPage",
        "GitHubLanguages",
        "GitHubTag",
        "GitHubTagPage",
    ):
        assert components[name]["additionalProperties"] is False, name

    assert components["Money"]["properties"]["currency"]["const"] == "USD"
    assert components["Money"]["properties"]["amountMinor"]["maximum"] == 9_007_199_254_740_991
    assert components["HelloCreate"]["properties"]["name"]["minLength"] == 1
    assert components["HelloCreate"]["properties"]["name"]["maxLength"] == 100
    name_pattern = components["HelloCreate"]["properties"]["name"]["pattern"]
    assert re.fullmatch(name_pattern, "Ada")
    assert re.fullmatch(name_pattern, " Ada") is None
    assert re.fullmatch(name_pattern, "Ada\u0085") is None
    assert components["ProfileUpdate"]["minProperties"] == 1
    assert "required" not in components["ProfileUpdate"]
    for component_name in ("ProfileCreate", "ProfileUpdate"):
        properties = components[component_name]["properties"]
        assert re.fullmatch(properties["contactEmail"]["pattern"], " Ada@EXAMPLE.COM ")
        assert re.fullmatch(properties["contactEmail"]["pattern"], "Ada@@example.com") is None
        assert re.fullmatch(properties["phoneNumber"]["pattern"], " +358401234567 ")
        assert re.fullmatch(properties["phoneNumber"]["pattern"], "+01234567") is None
    assert re.fullmatch(components["Profile"]["properties"]["contactEmail"]["pattern"], "Ada@example.com")
    assert re.fullmatch(components["Profile"]["properties"]["contactEmail"]["pattern"], " Ada@example.com ") is None
    assert components["Profile"]["properties"]["createdAt"]["format"] == "date-time"
    assert components["Profile"]["properties"]["createdAt"]["pattern"].endswith("Z$")
    assert "\\Z" not in components["GitHubOwner"]["properties"]["createdAt"]["pattern"]
    assert components["GitHubRepository"]["properties"]["topics"]["uniqueItems"] is True
    assert components["ErrorSource"]["oneOf"]

    operations = _operations(document)
    for key in (
        ("get", "/v1/items"),
        ("get", "/v1/github/owners/{owner}/repos"),
        ("get", "/v1/github/repos/{owner}/{repo}/activity"),
        ("get", "/v1/github/repos/{owner}/{repo}/tags"),
    ):
        cursor = next(parameter for parameter in operations[key]["parameters"] if parameter["name"] == "cursor")
        assert cursor["schema"]["pattern"] == "^[!-~]+$"
    repository = operations[("get", "/v1/github/repos/{owner}/{repo}")]
    repo = next(parameter for parameter in repository["parameters"] if parameter["name"] == "repo")
    assert re.fullmatch(repo["schema"]["pattern"], "portable.api")
    assert re.fullmatch(repo["schema"]["pattern"], "...") is None

    for reference in _references(document["paths"]):
        assert not reference.startswith(("http://", "https://"))
        _resolve(document, reference)


def test_openapi_application_schema_members_requiredness_and_nullability_are_exact(client: TestClient) -> None:
    components = client.get("/openapi.json").json()["components"]["schemas"]
    exact_members = {
        "HealthResponse": {"status"},
        "HelloCreate": {"name"},
        "Greeting": {"message"},
        "Money": {"amountMinor", "currency"},
        "Item": {"id", "name", "category", "price", "inStock", "createdAt", "description"},
        "ItemPage": {"items", "total"},
        "ProfileCreate": {
            "firstName",
            "lastName",
            "contactEmail",
            "phoneNumber",
            "marketingOptIn",
            "termsAccepted",
        },
        "ProfileUpdate": {"firstName", "lastName", "contactEmail", "phoneNumber", "marketingOptIn"},
        "Profile": {
            "id",
            "firstName",
            "lastName",
            "contactEmail",
            "phoneNumber",
            "marketingOptIn",
            "termsAccepted",
            "createdAt",
            "updatedAt",
        },
        "GitHubOwner": {
            "id",
            "login",
            "type",
            "name",
            "avatarUrl",
            "htmlUrl",
            "company",
            "blog",
            "location",
            "bio",
            "publicRepos",
            "followers",
            "following",
            "createdAt",
            "updatedAt",
        },
        "GitHubRepositorySummary": {"id", "name", "fullName", "description", "htmlUrl", "fork"},
        "GitHubRepository": {
            "id",
            "name",
            "fullName",
            "description",
            "htmlUrl",
            "fork",
            "language",
            "stargazersCount",
            "forksCount",
            "openIssuesCount",
            "archived",
            "createdAt",
            "updatedAt",
            "pushedAt",
            "defaultBranch",
            "license",
            "topics",
            "disabled",
        },
        "GitHubActivity": {"id", "actor", "actorAvatarUrl", "ref", "timestamp", "activityType"},
        "GitHubLanguage": {"name", "bytes"},
        "GitHubCommit": {"sha"},
        "GitHubTag": {"name", "commit"},
        "GitHubRepositoryPage": {"repos", "count"},
        "GitHubActivityPage": {"activities", "count"},
        "GitHubLanguages": {"languages"},
        "GitHubTagPage": {"tags", "count"},
    }
    for name, members in exact_members.items():
        schema = components[name]
        assert set(schema["properties"]) == members, name
        assert schema["additionalProperties"] is False, name
        if name == "ProfileUpdate":
            assert "required" not in schema
            assert schema["minProperties"] == 1
        elif name == "ProfileCreate":
            assert set(schema["required"]) == members - {"marketingOptIn"}
        else:
            assert set(schema["required"]) == members, name

    nullable = {
        "GitHubOwner": {"name", "company", "blog", "location", "bio"},
        "GitHubRepositorySummary": {"description"},
        "GitHubRepository": {"description", "language", "pushedAt", "license"},
        "GitHubActivity": {"actor", "actorAvatarUrl"},
    }
    for name, members in nullable.items():
        for member in members:
            assert {choice.get("type") for choice in components[name]["properties"][member]["anyOf"]} >= {"null"}

    for name, member in (
        ("ItemPage", "items"),
        ("GitHubRepositoryPage", "repos"),
        ("GitHubActivityPage", "activities"),
        ("GitHubTagPage", "tags"),
    ):
        assert components[name]["properties"][member]["maxItems"] == 100
    assert components["GitHubCommit"]["properties"]["sha"]["pattern"] == "^(?:[0-9a-f]{40}|[0-9a-f]{64})$"


def test_public_scalar_schemas_have_descriptions_and_examples(client: TestClient) -> None:
    components = client.get("/openapi.json").json()["components"]["schemas"]
    scalar_properties = {
        "HealthResponse": {"status"},
        "HelloCreate": {"name"},
        "Greeting": {"message"},
        "Money": {"amountMinor", "currency"},
        "Item": {"id", "name", "category", "inStock", "createdAt", "description"},
        "ItemPage": {"total"},
        "ProfileCreate": {
            "firstName",
            "lastName",
            "contactEmail",
            "phoneNumber",
            "marketingOptIn",
            "termsAccepted",
        },
        "ProfileUpdate": {"firstName", "lastName", "contactEmail", "phoneNumber", "marketingOptIn"},
        "Profile": {
            "id",
            "firstName",
            "lastName",
            "contactEmail",
            "phoneNumber",
            "marketingOptIn",
            "termsAccepted",
            "createdAt",
            "updatedAt",
        },
        "ProblemResponse": {"title", "status", "detail", "code"},
        "ValidationIssue": {"detail"},
        "GitHubOwner": {
            "id",
            "login",
            "type",
            "name",
            "avatarUrl",
            "htmlUrl",
            "company",
            "blog",
            "location",
            "bio",
            "publicRepos",
            "followers",
            "following",
            "createdAt",
            "updatedAt",
        },
        "GitHubRepositorySummary": {"id", "name", "fullName", "description", "htmlUrl", "fork"},
        "GitHubRepository": {
            "id",
            "name",
            "fullName",
            "description",
            "htmlUrl",
            "fork",
            "language",
            "stargazersCount",
            "forksCount",
            "openIssuesCount",
            "archived",
            "createdAt",
            "updatedAt",
            "pushedAt",
            "defaultBranch",
            "license",
            "topics",
            "disabled",
        },
        "GitHubActivity": {"id", "actor", "actorAvatarUrl", "ref", "timestamp", "activityType"},
        "GitHubLanguage": {"name", "bytes"},
        "GitHubCommit": {"sha"},
        "GitHubTag": {"name"},
        "GitHubRepositoryPage": {"count"},
        "GitHubActivityPage": {"count"},
        "GitHubTagPage": {"count"},
    }

    for component_name, property_names in scalar_properties.items():
        properties = components[component_name]["properties"]
        for property_name in property_names:
            schema = properties[property_name]
            assert schema.get("description"), (component_name, property_name)
            assert schema.get("examples"), (component_name, property_name)

    for variant in components["ErrorSource"]["oneOf"]:
        assert len(variant["properties"]) == 1
        property_name, schema = next(iter(variant["properties"].items()))
        assert schema.get("description"), ("ErrorSource", property_name)
        assert schema.get("examples"), ("ErrorSource", property_name)

    operations = _operations(client.get("/openapi.json").json())
    for operation_key, operation in operations.items():
        for status, response in operation["responses"].items():
            if int(status) < 300:
                continue
            for media in response["content"].values():
                properties = media["schema"]["properties"]
                for property_name in ("title", "status", "detail", "code"):
                    assert properties[property_name].get("description"), (operation_key, status, property_name)
                    assert properties[property_name].get("examples"), (operation_key, status, property_name)


def test_openapi_discovery_is_local_and_rejects_request_variants_without_dependencies(
    client: TestClient,
    mock_profile_service: AsyncMock,
    mock_github_service: AsyncMock,
) -> None:
    from app.main import fastapi_app

    verifier = AsyncMock(side_effect=AssertionError("discovery authenticated"))
    fastapi_app.dependency_overrides[verify_firebase_token] = verifier
    try:
        success = client.get("/openapi.json", headers={"X-Request-ID": "discovery-local"})
        assert success.status_code == 200
        assert success.headers["X-Request-ID"] == "discovery-local"
        assert success.json()["info"]["version"] == fastapi_app.version
        for target in ("/openapi.json?unknown=1", "/openapi.json?x=1&x=2", "/openapi.json?x=%FF"):
            response = client.get(target)
            assert response.status_code == 400
            assert response.json()["code"] == "invalid_request"
        negotiation = client.get("/openapi.json", headers={"Accept": "application/cbor"})
        assert negotiation.status_code == 406
        assert negotiation.headers["Content-Type"] == "application/cbor"
        assert cbor2.loads(negotiation.content)["code"] == "not_acceptable"
        method = client.post("/openapi.json", content=b"must-not-be-read")
        assert method.status_code == 405
        assert method.headers["Allow"] == "GET"
    finally:
        fastapi_app.dependency_overrides.pop(verify_firebase_token, None)
    verifier.assert_not_awaited()
    for service_method in (
        mock_profile_service.create_profile,
        mock_profile_service.get_profile,
        mock_profile_service.update_profile,
        mock_profile_service.delete_profile,
        mock_github_service.get_owner,
        mock_github_service.get_repository,
    ):
        service_method.assert_not_awaited()


@pytest.mark.parametrize("query", ["unknown=1", "unknown=1&unknown=2", "unknown=%FF"])
def test_standalone_schema_discovery_rejects_unknown_repeated_and_malformed_query(
    client: TestClient,
    query: str,
) -> None:
    response = client.get(f"/schemas/Profile.json?{query}")

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
