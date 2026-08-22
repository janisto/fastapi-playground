"""Real FastAPI boundary tests for dependency-free portable operations."""

import re
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import cbor2
import httpx2
import pytest
from fastapi.testclient import TestClient

from app.auth.firebase import verify_firebase_token


def _assert_common_headers(response: httpx2.Response, request_id: str | None = None) -> None:
    selected = response.headers["X-Request-ID"]
    if request_id is None:
        assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", selected)
    else:
        assert selected == request_id
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Accept" in response.headers["Vary"].split(", ")


def _problem(response: httpx2.Response, status: int, code: str) -> dict[str, object]:
    assert response.status_code == status
    assert response.headers["Content-Type"].split(";", maxsplit=1)[0] == "application/problem+json"
    body = response.json()
    assert body["status"] == status
    assert body["code"] == code
    assert "input" not in str(body).lower()
    _assert_common_headers(response)
    return body


def _link_target(value: str, relation: str) -> str:
    for part in value.split(", "):
        if f'rel="{relation}"' in part:
            return part.split(">", maxsplit=1)[0].removeprefix("<")
    raise AssertionError(f"missing {relation}")


def test_health_and_hello_exact_json_and_cbor(client: TestClient) -> None:
    health = client.get("/health", headers={"X-Request-ID": "A._:-9"})
    assert health.status_code == 200
    assert health.json() == {"status": "healthy"}
    _assert_common_headers(health, "A._:-9")

    health_cbor = client.get("/health", headers={"Accept": "application/cbor"})
    assert health_cbor.status_code == 200
    assert health_cbor.headers["Content-Type"] == "application/cbor"
    assert cbor2.loads(health_cbor.content) == {"status": "healthy"}

    default = client.get("/v1/hello")
    assert default.status_code == 200
    assert default.json() == {"message": "Hello, World!"}
    _assert_common_headers(default)

    created = client.post(
        "/v1/hello",
        content=cbor2.dumps({"name": "Åda"}),
        headers={"Content-Type": "application/cbor", "Accept": "application/cbor"},
    )
    assert created.status_code == 200
    assert created.headers["Content-Type"] == "application/cbor"
    assert cbor2.loads(created.content) == {"message": "Hello, Åda!"}
    assert "Location" not in created.headers
    _assert_common_headers(created)


@pytest.mark.parametrize(
    ("content", "content_type", "status", "code"),
    [
        (b'{"name":"Ada","name":"Grace"}', "application/json", 400, "invalid_request"),
        (b"\xef\xbb\xbf" + b'{"name":"Ada"}', "application/json", 400, "invalid_request"),
        (b'{"name":NaN}', "application/json", 400, "invalid_request"),
        (b'{"name":"\\ud800"}', "application/json", 400, "invalid_request"),
        (b'{"name":"Ada"} trailing', "application/json", 400, "invalid_request"),
        (b'{"name":"\xff"}', "application/json", 400, "invalid_request"),
        (b'["Ada"]', "application/json", 422, "validation_failed"),
        (b"\xa2\x64name\x63Ada\x64name\x65Grace", "application/cbor", 400, "invalid_request"),
        (cbor2.dumps({"name": "Ada"}) + cbor2.dumps(1), "application/cbor", 400, "invalid_request"),
        (b"\xa1", "application/cbor", 400, "invalid_request"),
        (cbor2.dumps({"name": float("nan")}), "application/cbor", 422, "validation_failed"),
        (b'{"name":null}', "application/json", 422, "validation_failed"),
        (b'{"name":" Ada"}', "application/json", 422, "validation_failed"),
        (b'{"name":"Ada","extra":true}', "application/json", 422, "validation_failed"),
        (b'{"name":"Ada"}', "text/plain", 415, "unsupported_media_type"),
        (b'{"name":"Ada"}', 'application/json; charset="UTF-8"junk', 415, "unsupported_media_type"),
        (b'{"name":"Ada"}', "application/json; charset=utf-8; charset=utf-8", 415, "unsupported_media_type"),
        (b'{"name":"Ada"}', "application/json; charset =utf-8", 415, "unsupported_media_type"),
        (b'{"name":"Ada"}', "application/json; charset= utf-8", 415, "unsupported_media_type"),
        (b'{"name":"Ada"}', "application/cbor; charset=utf-8", 415, "unsupported_media_type"),
        (b'{"name":"Ada"}', None, 415, "unsupported_media_type"),
        (b"", "application/json", 400, "invalid_request"),
        (b"", None, 400, "invalid_request"),
        (b"", "text/plain", 415, "unsupported_media_type"),
    ],
)
def test_hello_parser_validation_and_media_split(
    client: TestClient,
    content: bytes,
    content_type: str | None,
    status: int,
    code: str,
) -> None:
    headers = {} if content_type is None else {"Content-Type": content_type}
    response = client.post("/v1/hello", content=content, headers=headers)
    body = _problem(response, status, code)
    if code == "validation_failed":
        assert body["errors"]
        assert content.decode("utf-8", errors="ignore") not in str(body)


def test_missing_member_points_only_to_the_existing_document(client: TestClient) -> None:
    response = client.post("/v1/hello", json={})
    body = _problem(response, 422, "validation_failed")
    assert body["errors"] == [{"detail": "Request field is required", "source": {"pointer": "/"}}]


def test_json_quoted_charset_and_content_coding_are_strict(client: TestClient) -> None:
    accepted = client.post(
        "/v1/hello",
        content=b'{"name":"Ada"}',
        headers={"Content-Type": 'application/json; charset="UTF\\-8"', "Content-Encoding": "identity"},
    )
    assert accepted.status_code == 200

    for headers in (
        [("Content-Type", "application/json"), ("Content-Encoding", "identity, gzip")],
        [("Content-Type", "application/json"), ("Content-Encoding", "identity"), ("Content-Encoding", "identity")],
        [("Content-Type", "application/json"), ("Content-Encoding", "gzip")],
        [("Content-Type", "application/json"), ("Content-Encoding", "")],
        [("Content-Type", "application/json"), ("Content-Type", "application/json")],
        [("Content-Type", "application/json, application/json")],
    ):
        response = client.post("/v1/hello", content=b'{"name":"Ada"}', headers=headers)
        _problem(response, 415, "unsupported_media_type")


def test_negotiation_specificity_charset_and_error_fallback(client: TestClient) -> None:
    empty = client.get("/health", headers={"Accept": ""})
    _problem(empty, 406, "not_acceptable")

    charset = client.get("/health", headers={"Accept": "application/json; charset=UTF-8"})
    assert charset.status_code == 200
    assert charset.headers["Content-Type"].lower() == "application/json; charset=utf-8"

    post_weight_charset = client.get("/health", headers={"Accept": "application/json;q=0.5;charset=utf-8"})
    assert post_weight_charset.status_code == 200
    assert post_weight_charset.headers["Content-Type"].lower() == "application/json; charset=utf-8"

    _problem(
        client.get("/health", headers={"Accept": "application/json;q=0.5;profile=x"}),
        406,
        "not_acceptable",
    )

    rejected = client.post(
        "/v1/hello",
        content=b'{"name":"Ada"}',
        headers={"Content-Type": "application/json", "Accept": "text/plain"},
    )
    _problem(rejected, 406, "not_acceptable")

    cbor_error = client.post(
        "/v1/hello",
        content=b'{"name":null}',
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json;q=1, application/cbor;q=0.5",
        },
    )
    assert cbor_error.status_code == 422
    assert cbor_error.headers["Content-Type"] == "application/cbor"
    assert cbor2.loads(cbor_error.content)["code"] == "validation_failed"


@pytest.mark.parametrize("size", [999_999, 1_000_000])
def test_hello_accepts_exact_inbound_boundaries(client: TestClient, size: int) -> None:
    prefix = b'{"name":"Ada"}'
    response = client.post(
        "/v1/hello",
        content=prefix + b" " * (size - len(prefix)),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, Ada!"}


def test_hello_rejects_first_over_limit_byte(client: TestClient) -> None:
    prefix = b'{"name":"Ada"}'
    response = client.post(
        "/v1/hello",
        content=prefix + b" " * (1_000_001 - len(prefix)),
        headers={"Content-Type": "application/json", "X-Request-ID": "limit-case"},
    )
    _problem(response, 413, "payload_too_large")
    _assert_common_headers(response, "limit-case")


def test_items_catalog_filter_and_bidirectional_links(client: TestClient) -> None:
    first = client.get("/v1/items?limit=10")
    assert first.status_code == 200
    assert first.json()["total"] == 30
    assert [item["id"] for item in first.json()["items"]] == [f"item-{number:03d}" for number in range(1, 11)]
    assert first.json()["items"][0]["price"] == {"amountMinor": 2999, "currency": "USD"}
    assert 'rel="prev"' not in first.headers["Link"]

    second_target = _link_target(first.headers["Link"], "next")
    second = client.get(second_target)
    assert [item["id"] for item in second.json()["items"]] == [f"item-{number:03d}" for number in range(11, 21)]
    assert {'rel="next"', 'rel="prev"'} <= {
        part.partition(";")[2].strip() for part in second.headers["Link"].split(", ")
    }

    third = client.get(_link_target(second.headers["Link"], "next"))
    assert [item["id"] for item in third.json()["items"]] == [f"item-{number:03d}" for number in range(21, 31)]
    assert 'rel="next"' not in third.headers["Link"]
    back = client.get(_link_target(third.headers["Link"], "prev"))
    assert back.json() == second.json()

    filtered = client.get("/v1/items?category=electronics&limit=100")
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 13
    assert all(item["category"] == "electronics" for item in filtered.json()["items"])
    assert "Link" not in filtered.headers


def test_items_default_page_and_every_exact_category_subset(client: TestClient) -> None:
    first = client.get("/v1/items")
    assert first.status_code == 200
    assert first.json()["total"] == 30
    assert [item["id"] for item in first.json()["items"]] == [f"item-{number:03d}" for number in range(1, 21)]
    assert 'rel="prev"' not in first.headers["Link"]
    second = client.get(_link_target(first.headers["Link"], "next"))
    assert [item["id"] for item in second.json()["items"]] == [f"item-{number:03d}" for number in range(21, 31)]
    assert second.json()["total"] == 30
    assert 'rel="prev"' in second.headers["Link"]
    assert 'rel="next"' not in second.headers["Link"]

    expected = {
        "electronics": [1, 2, 4, 5, 8, 9, 10, 15, 16, 25, 26, 28, 29],
        "tools": [3, 21, 22, 23, 24, 27],
        "accessories": [6, 7, 20, 30],
        "robotics": [11, 12],
        "power": [13, 14],
        "components": [17, 18, 19],
    }
    for category, numbers in expected.items():
        response = client.get(f"/v1/items?category={category}&limit=100")
        assert response.status_code == 200
        assert response.json()["total"] == len(numbers)
        assert [item["id"] for item in response.json()["items"]] == [f"item-{number:03d}" for number in numbers]


@pytest.mark.parametrize(
    ("query", "status", "code"),
    [
        ("unknown=1", 400, "invalid_request"),
        ("limit=1&limit=2", 400, "invalid_request"),
        ("limit=%FF", 400, "invalid_request"),
        ("limit=%", 400, "invalid_request"),
        ("limit=%GG", 400, "invalid_request"),
        ("limit=1.0", 422, "validation_failed"),
        ("limit=0", 422, "validation_failed"),
        ("limit=101", 422, "validation_failed"),
        (f"limit={'9' * 5000}", 422, "validation_failed"),
        ("category=other", 422, "validation_failed"),
        ("cursor=", 400, "invalid_request"),
        ("cursor=not-a-cursor", 400, "invalid_request"),
    ],
)
def test_items_closed_query_and_typed_split(client: TestClient, query: str, status: int, code: str) -> None:
    _problem(client.get(f"/v1/items?{query}"), status, code)


def test_items_normalizes_overlong_zero_padding_before_handler_conversion(client: TestClient) -> None:
    response = client.get(f"/v1/items?limit={'0' * 5000}1")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["item-001"]
    next_target = _link_target(response.headers["Link"], "next")
    assert parse_qs(urlsplit(next_target).query)["limit"] == ["1"]


def test_known_method_trailing_path_and_request_id_replacement(client: TestClient) -> None:
    method = client.put("/v1/hello", content=b"must-not-be-read")
    body = _problem(method, 405, "method_not_allowed")
    assert method.headers["Allow"] == "GET, POST"
    assert body["detail"] == "Method not allowed"

    missing = client.get("/v1/hello/")
    _problem(missing, 404, "not_found")
    assert "location" not in missing.headers

    invalid = client.get("/health", headers={"X-Request-ID": "bad value"})
    _assert_common_headers(invalid)
    assert invalid.headers["X-Request-ID"] != "bad value"

    maximum = "A" + "._:-" * 31 + "xyz"
    assert len(maximum) == 128
    accepted = client.get("/health", headers={"X-Request-ID": maximum})
    _assert_common_headers(accepted, maximum)


def test_item_links_are_relative_and_preserve_only_validated_scope(client: TestClient) -> None:
    response = client.get(
        "/v1/items?category=tools&limit=2",
        headers={"Host": "attacker.example", "X-Forwarded-Host": "evil.example"},
    )
    target = _link_target(response.headers["Link"], "next")
    parsed = urlsplit(target)
    assert parsed.scheme == parsed.netloc == ""
    assert parsed.path == "/v1/items"
    assert parse_qs(parsed.query)["category"] == ["tools"]
    assert parse_qs(parsed.query)["limit"] == ["2"]


def test_public_local_families_do_not_invoke_authentication_or_external_services(
    client: TestClient,
    mock_profile_service: AsyncMock,
    mock_github_service: AsyncMock,
) -> None:
    from app.main import fastapi_app

    verifier = AsyncMock(side_effect=AssertionError("public operation authenticated"))
    fastapi_app.dependency_overrides[verify_firebase_token] = verifier
    try:
        assert client.get("/health").status_code == 200
        assert client.get("/v1/hello").status_code == 200
        assert client.post("/v1/hello", json={"name": "Ada"}).status_code == 200
        assert client.get("/v1/items").status_code == 200
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
        mock_github_service.list_owner_repositories,
    ):
        service_method.assert_not_awaited()
