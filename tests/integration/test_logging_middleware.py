"""Integration tests for logging middleware and health endpoint."""

from fastapi.testclient import TestClient


def test_trace_injection(client: TestClient) -> None:
    # Simulate Cloud Trace header
    trace_header = "0123456789abcdef0123456789abcdef/123456;o=1"
    res = client.get("/health", headers={"X-Cloud-Trace-Context": trace_header})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
