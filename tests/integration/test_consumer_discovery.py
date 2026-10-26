"""Origin-based discovery, same-build guides, and dependency isolation."""

from pathlib import Path
from unittest.mock import Mock
from urllib.parse import urljoin

import cbor2
import httpx2
import pytest
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.auth.firebase import verify_firebase_token
from app.dependencies import get_github_service, get_profile_service

_ROOT = Path(__file__).resolve().parents[2]
_CATALOG_TYPE = 'application/linkset+json; profile="https://www.rfc-editor.org/info/rfc9727"'
_INDEX = ("/llms.txt", "describedby", "text/plain")


def _links(response: httpx2.Response) -> set[tuple[str, str | None, str | None]]:
    links = set()
    for value in response.headers.get_list("link", split_commas=True):
        parsed = httpx2.Response(200, headers={"Link": value}).links
        links.update((link["url"], link.get("rel"), link.get("type")) for link in parsed.values())
    return links


def test_catalog_bootstraps_same_build_targets_without_dependencies(
    client: TestClient,
    mocker: MockerFixture,
) -> None:
    from app.main import fastapi_app

    forbidden = Mock(side_effect=AssertionError("discovery invoked a dependency"))
    for dependency in (verify_firebase_token, get_profile_service, get_github_service):
        fastapi_app.dependency_overrides[dependency] = forbidden
    initialize = mocker.patch(
        "app.core.firebase.initialize_firebase", side_effect=AssertionError("Firebase initialized")
    )
    outbound = mocker.patch("httpx2.AsyncClient.send", side_effect=AssertionError("outbound request"))
    dns = mocker.patch("socket.getaddrinfo", side_effect=AssertionError("DNS lookup"))

    response = client.get("/.well-known/api-catalog")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == _CATALOG_TYPE
    document = response.json()
    assert set(document) == {"linkset"}
    assert len(document["linkset"]) == 1
    context = document["linkset"][0]
    assert context["anchor"] == "/"
    expected = {
        "service-desc": {("/openapi.json", "application/json")},
        "service-doc": {("/llms.txt", "text/plain"), ("/llms-full.txt", "text/plain")},
        "status": {("/health", "application/json")},
    }
    assert set(context) == {"anchor", *expected}
    assert urljoin(str(response.url), context["anchor"]) == "http://testserver/"
    for relation, targets in expected.items():
        assert {(link["href"], link["type"]) for link in context[relation]} == targets
        for link in context[relation]:
            target = urljoin(str(response.url), link["href"])
            resolved = client.get(target, headers={"Accept": link["type"]})
            assert resolved.status_code == 200
            assert resolved.headers["Content-Type"].split(";", 1)[0] == link["type"]
            if relation == "service-desc":
                assert resolved.json()["openapi"].startswith("3.1.")
            elif relation == "status":
                assert resolved.json() == {"status": "healthy"}
            else:
                assert resolved.content == (_ROOT / link["href"].lstrip("/")).read_bytes()
    forbidden.assert_not_called()
    initialize.assert_not_called()
    outbound.assert_not_called()
    dns.assert_not_called()


def test_catalog_head_preserves_get_metadata_and_typed_links(client: TestClient) -> None:
    headers = {"X-Request-ID": "catalog-metadata"}
    get = client.get("/.well-known/api-catalog", headers=headers)
    head = client.head("/.well-known/api-catalog", headers=headers)
    assert head.status_code == 200
    assert head.content == b""
    for name in ("Content-Type", "Content-Length", "Cache-Control", "Vary", "Link", "X-Request-ID"):
        assert head.headers[name] == get.headers[name]
    assert int(head.headers["Content-Length"]) == len(get.content)
    for response in (get, head):
        assert ("/.well-known/api-catalog", "api-catalog", "application/linkset+json") in _links(response)
        assert _INDEX in _links(response)


@pytest.mark.parametrize("path", ["/llms.txt", "/llms-full.txt"])
def test_guides_are_exact_utf8_files_with_shared_response_headers(client: TestClient, path: str) -> None:
    response = client.get(path, headers={"X-Request-ID": "guide-content"})
    assert response.status_code == 200
    assert response.content == (_ROOT / path[1:]).read_bytes()
    assert response.content.decode("utf-8").startswith("# FastAPI Playground")
    assert response.headers["Content-Type"] == "text/plain; charset=utf-8"
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Request-ID"] == "guide-content"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "accept" in response.headers["Vary"].lower()


@pytest.mark.parametrize(
    ("path", "accept", "status"),
    [
        ("/.well-known/api-catalog", "application/linkset+json", 200),
        ("/.well-known/api-catalog", _CATALOG_TYPE, 200),
        ("/.well-known/api-catalog", "application/*", 200),
        ("/.well-known/api-catalog", 'application/linkset+json; profile="https://example.test/wrong"', 406),
        ("/.well-known/api-catalog", "application/json", 406),
        ("/.well-known/api-catalog", "application/cbor", 406),
        ("/.well-known/api-catalog", "application/linkset+json;q=0, */*;q=1", 406),
        ("/llms.txt", "text/plain", 200),
        ("/llms-full.txt", "text/plain; charset=utf-8", 200),
        ("/llms.txt", "text/plain; charset=iso-8859-1", 406),
        ("/llms-full.txt", "text/plain;q=0, */*;q=1", 406),
        ("/llms.txt", "application/json", 406),
        ("/llms-full.txt", "application/cbor", 406),
    ],
)
def test_documentation_negotiates_only_its_actual_representation(
    client: TestClient, path: str, accept: str, status: int
) -> None:
    response = client.get(path, headers={"Accept": accept})
    assert response.status_code == status
    if status == 406:
        assert response.headers["Content-Type"] == "application/problem+json"
        assert response.json()["code"] == "not_acceptable"


@pytest.mark.parametrize("path", ["/.well-known/api-catalog", "/llms.txt", "/llms-full.txt"])
@pytest.mark.parametrize("query", ["unknown=1", "x=1&x=2", "x=%FF", "x=%zz"])
def test_documentation_rejects_query_before_serving_content(client: TestClient, path: str, query: str) -> None:
    response = client.get(f"{path}?{query}", headers={"Accept": "application/cbor"})
    assert response.status_code == 400
    assert response.headers["Content-Type"] == "application/problem+json"
    assert response.json() == {
        "title": "Bad Request",
        "status": 400,
        "detail": "Request is malformed",
        "code": "invalid_request",
    }


@pytest.mark.parametrize(
    ("path", "allow"),
    [("/.well-known/api-catalog", {"GET", "HEAD"}), ("/llms.txt", {"GET"}), ("/llms-full.txt", {"GET"})],
)
def test_documentation_rejects_unsupported_methods_with_truthful_allow(
    client: TestClient, path: str, allow: set[str]
) -> None:
    response = client.post(path, content=b"not read", headers={"Accept": "application/cbor"})
    assert response.status_code == 405
    assert set(response.headers["Allow"].split(", ")) == allow
    assert response.headers["Content-Type"] == "application/problem+json"
    assert response.json()["code"] == "method_not_allowed"


@pytest.mark.parametrize("accept", ["application/json", "application/cbor"])
def test_health_links_work_for_every_success_representation(client: TestClient, accept: str) -> None:
    response = client.get("/health", headers={"Accept": accept})
    assert response.status_code == 200
    body = cbor2.loads(response.content) if accept == "application/cbor" else response.json()
    assert body == {"status": "healthy"}
    assert {
        ("/.well-known/api-catalog", "api-catalog", "application/linkset+json"),
        ("/openapi.json", "service-desc", "application/json"),
    } <= _links(response)
    header = client.get("/openapi.json").json()["paths"]["/health"]["get"]["responses"]["200"]["headers"]["Link"]
    assert header["required"] is True
    assert header["schema"]["type"] == "string"


@pytest.mark.parametrize("path", ["/openapi.json", "/llms-full.txt", "/api-docs", "/api-redoc"])
def test_documentation_advertises_a_followable_same_build_index(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 200
    assert _INDEX in _links(response)
    index = client.get(urljoin(str(response.url), _INDEX[0]))
    assert index.status_code == 200
    assert index.content == (_ROOT / "llms.txt").read_bytes()


def test_ui_index_link_preserves_other_links_including_another_describedby(
    client: TestClient, mocker: MockerFixture
) -> None:
    source_link = '</schemas/Profile.json>; rel="describedby"; type="application/schema+json"'
    mocker.patch("app.main.get_swagger_ui_html", return_value=HTMLResponse("docs", headers={"Link": source_link}))
    response = client.get("/api-docs")
    assert response.status_code == 200
    assert _links(response) == {_INDEX, ("/schemas/Profile.json", "describedby", "application/schema+json")}


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_catalog_serialization_failure_is_safe_json_and_head_is_empty(
    client: TestClient, mocker: MockerFixture, method: str
) -> None:
    mocker.patch("app.api.discovery.JSONResponse", side_effect=ValueError("private/path credential-secret"))
    response = client.request(method, "/.well-known/api-catalog", headers={"Accept": "application/linkset+json"})
    assert response.status_code == 500
    assert response.headers["Content-Type"] == "application/problem+json"
    if method == "HEAD":
        assert response.content == b""
    else:
        assert response.json() == {
            "title": "Internal Server Error",
            "status": 500,
            "detail": "Internal server error",
            "code": "internal_error",
        }
    assert b"credential-secret" not in response.content


@pytest.mark.parametrize("path", ["/README.md", "/AGENTS.md", "/.git/config", "/llms.txt/extra", "/.well-known/"])
def test_discovery_does_not_expose_the_repository(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_browser_catalog_head_preflight_and_discovery_links_are_accessible() -> None:
    from app.core.config import Settings
    from app.main import _build_application, fastapi_app

    origin = "https://client.example.test"
    settings = Settings(_env_file=None, cors_origins=[origin])
    with TestClient(_build_application(fastapi_app, settings)) as client:
        preflight = client.options(
            "/.well-known/api-catalog",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "HEAD",
                "Access-Control-Request-Headers": "X-Request-ID",
            },
        )
        assert preflight.status_code == 200
        assert "HEAD" in preflight.headers["Access-Control-Allow-Methods"].split(", ")
        response = client.head(
            "/.well-known/api-catalog", headers={"Origin": origin, "X-Request-ID": "browser-catalog"}
        )
        assert response.status_code == 200
        assert response.content == b""
        assert response.headers["Access-Control-Allow-Origin"] == origin
        exposed = {name.strip().lower() for name in response.headers["Access-Control-Expose-Headers"].split(",")}
        assert {"link", "x-request-id"} <= exposed
        assert _INDEX in _links(response)
