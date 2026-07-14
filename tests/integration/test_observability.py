"""
Integration tests for request observability wiring.
"""

import json
import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient
from fastapi_request_observability import JSONFormatter, LoggingPreset

from app.auth.firebase import verify_firebase_token
from app.core.config import get_settings


def _access_payloads(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    """
    Format captured access records using the production logging preset.
    """
    formatter = JSONFormatter(LoggingPreset.GCP)
    return [json.loads(formatter.format(record)) for record in caplog.records if record.name == "http.access"]


def test_emits_correlated_gcp_access_record(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Verify one access record includes the response request ID and route metadata.
    """
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    traceparent = f"00-{trace_id}-00f067aa0ba902b7-01"

    with caplog.at_level(logging.INFO, logger="http.access"):
        response = client.get(
            "/health",
            headers={
                "X-Request-ID": "health-check-123",
                "traceparent": traceparent,
            },
        )

    payloads = _access_payloads(caplog)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["message"] == "request completed"
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["correlation_id"] == trace_id
    assert payload["logging.googleapis.com/trace"] == trace_id
    assert payload["path_template"] == "/health"
    assert payload["operation_id"] == "health_get"
    assert payload["status"] == 200
    assert payload["httpRequest"]["status"] == 200
    assert "logging.googleapis.com/spanId" not in payload


def test_access_record_uses_full_prefixed_route_template(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Verify observability identifies the public route instead of its unprefixed router path.
    """
    with caplog.at_level(logging.INFO, logger="http.access"):
        response = client.get("/v1/hello")

    assert response.status_code == 200
    payloads = _access_payloads(caplog)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["path_template"] == "/v1/hello"
    assert payload["operation_id"] == "hello_get"


def test_unhandled_failure_emits_one_correlated_access_record(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Verify an unexpected dependency failure still emits one complete access record.
    """
    from app.main import fastapi_app

    request_id = "failed-profile-request"

    async def fail_authentication() -> None:
        raise RuntimeError("synthetic dependency failure")

    fastapi_app.dependency_overrides[verify_firebase_token] = fail_authentication
    try:
        with caplog.at_level(logging.INFO, logger="http.access"):
            response = client.get("/v1/profile", headers={"X-Request-ID": request_id})
    finally:
        fastapi_app.dependency_overrides.pop(verify_firebase_token, None)

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == request_id
    payloads = _access_payloads(caplog)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["request_id"] == request_id
    assert payload["status"] == 500
    assert payload["httpRequest"]["status"] == 500
    assert payload["path_template"] == "/v1/profile"
    assert payload["operation_id"] == "profile_get"


def test_body_limit_rejection_emits_one_correlated_access_record(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Verify middleware-generated 413 responses retain access logging and correlation.
    """
    request_id = "oversized-request"
    headers = {
        "Content-Length": str(get_settings().max_request_size_bytes + 1),
        "Content-Type": "application/json",
        "X-Request-ID": request_id,
    }

    with caplog.at_level(logging.INFO, logger="http.access"):
        response = client.post("/v1/hello", content=b"", headers=headers)

    assert response.status_code == 413
    assert response.headers["X-Request-ID"] == request_id
    payloads = _access_payloads(caplog)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["request_id"] == request_id
    assert payload["status"] == 413
    assert payload["httpRequest"]["status"] == 413
