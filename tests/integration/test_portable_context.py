"""Request-context and observability integration tests."""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from fastapi_request_observability import JSONFormatter, LoggingPreset

from app.exceptions import ProfileDependencyError


def _generated(value: str) -> bool:
    return len(value) == 32 and value == value.lower() and all(character in "0123456789abcdef" for character in value)


def _access_payloads(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    formatter = JSONFormatter(preset=LoggingPreset.GCP)
    return [json.loads(formatter.format(record)) for record in caplog.records if record.name == "http.access"]


@pytest.mark.parametrize(
    "candidate",
    ["", "bad value", b"\xe5", "A" * 129, "one,two", "/path", '"quote"'],
)
def test_invalid_request_ids_are_replaced_not_reflected(client: TestClient, candidate: str | bytes) -> None:
    if isinstance(candidate, bytes):
        response = client.get("/health", headers=[(b"X-Request-ID", candidate)])
    else:
        response = client.get("/health", headers=[("X-Request-ID", candidate)])
    assert response.status_code == 200
    incoming = candidate.decode("latin1") if isinstance(candidate, bytes) else candidate
    assert response.headers["X-Request-ID"] != incoming
    assert _generated(response.headers["X-Request-ID"])


def test_repeated_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health", headers=[("X-Request-ID", "one"), ("X-Request-ID", "two")])
    assert _generated(response.headers["X-Request-ID"])


@pytest.mark.parametrize("candidate", ["A", "A._:-9", "A" * 128])
def test_valid_request_id_boundaries_and_punctuation_are_preserved(client: TestClient, candidate: str) -> None:
    response = client.get("/health", headers={"X-Request-ID": candidate})
    assert response.headers.get_list("X-Request-ID") == [candidate]


def test_generated_ids_are_unique_under_concurrent_requests(client: TestClient) -> None:
    with ThreadPoolExecutor(max_workers=8) as executor:
        values = list(executor.map(lambda _: client.get("/health").headers["X-Request-ID"], range(32)))
    assert len(set(values)) == len(values)
    assert all(_generated(value) for value in values)


@pytest.mark.parametrize(
    ("method", "target", "kwargs", "status"),
    [
        ("GET", "/health", {}, 200),
        ("GET", "/missing", {}, 404),
        ("PUT", "/v1/hello", {"content": b"unread"}, 405),
        (
            "POST",
            "/v1/hello",
            {"content": b"x", "headers": {"Content-Length": "1000001", "Content-Type": "application/json"}},
            413,
        ),
        ("POST", "/v1/hello", {"json": {"name": None}}, 422),
    ],
)
def test_selected_request_id_survives_representative_outcomes(
    client: TestClient,
    method: str,
    target: str,
    kwargs: dict[str, Any],
    status: int,
) -> None:
    request_arguments = dict(kwargs)
    headers = {**request_arguments.pop("headers", {}), "X-Request-ID": "selected-id"}
    response = client.request(method, target, headers=headers, **request_arguments)
    assert response.status_code == status
    assert response.headers.get_list("X-Request-ID") == ["selected-id"]


def test_selected_request_id_survives_authentication_and_dependency_failures(
    client: TestClient,
    with_fake_user: None,
    mock_profile_service: AsyncMock,
) -> None:
    from app.auth.firebase import verify_firebase_token
    from app.main import fastapi_app

    fastapi_app.dependency_overrides.pop(verify_firebase_token, None)
    unauthorized = client.get("/v1/profile", headers={"X-Request-ID": "auth-id"})
    assert unauthorized.status_code == 401
    assert unauthorized.headers.get_list("X-Request-ID") == ["auth-id"]

    from tests.helpers.auth import make_fake_user

    fastapi_app.dependency_overrides[verify_firebase_token] = make_fake_user
    mock_profile_service.get_profile.side_effect = ProfileDependencyError
    unavailable = client.get(
        "/v1/profile",
        headers={"Authorization": "ignored", "X-Request-ID": "dependency-id"},
    )
    assert unavailable.status_code == 503
    assert unavailable.headers.get_list("X-Request-ID") == ["dependency-id"]


def test_access_record_uses_selected_id_trace_and_portable_operation_id(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    with caplog.at_level(logging.INFO, logger="http.access"):
        response = client.get(
            "/health",
            headers={
                "X-Request-ID": "health-check-123",
                "traceparent": f"00-{trace_id}-00f067aa0ba902b7-01",
            },
        )
    payloads = _access_payloads(caplog)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["request_id"] == response.headers["X-Request-ID"] == "health-check-123"
    assert payload["correlation_id"] == trace_id
    assert payload["path_template"] == "/health"
    assert payload["operation_id"] == "getHealth"
    assert payload["status"] == 200
    assert "path" not in payload
    assert "peer_ip" not in payload
    assert "user_agent" not in payload


def test_recovered_failure_is_safe_and_emits_one_correlated_terminal_record(
    client: TestClient,
    with_fake_user: None,
    mock_profile_service: AsyncMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    del with_fake_user
    mock_profile_service.get_profile.side_effect = RuntimeError("SECRET provider and profile value")
    with caplog.at_level(logging.INFO):
        response = client.get(
            "/v1/profile",
            headers={"Authorization": "ignored", "X-Request-ID": "failure-id"},
        )
    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "failure-id"
    assert response.json() == {
        "title": "Internal Server Error",
        "status": 500,
        "detail": "Internal server error",
        "code": "internal_error",
    }
    assert "SECRET" not in response.text
    assert "SECRET" not in "\n".join(record.getMessage() for record in caplog.records)
    payloads = _access_payloads(caplog)
    assert len(payloads) == 1
    assert payloads[0]["request_id"] == "failure-id"
    assert payloads[0]["operation_id"] == "getProfile"
    assert payloads[0]["status"] == 500
