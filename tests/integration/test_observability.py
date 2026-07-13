"""
Integration tests for request observability wiring.
"""

import json
import logging

import pytest
from fastapi.testclient import TestClient
from fastapi_request_observability import JSONFormatter, LoggingPreset


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

    access_records = [record for record in caplog.records if record.name == "http.access"]
    assert len(access_records) == 1

    payload = json.loads(JSONFormatter(LoggingPreset.GCP).format(access_records[0]))
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
    access_records = [record for record in caplog.records if record.name == "http.access"]
    assert len(access_records) == 1

    payload = json.loads(JSONFormatter(LoggingPreset.GCP).format(access_records[0]))
    assert payload["path_template"] == "/v1/hello"
    assert payload["operation_id"] == "hello_get"
