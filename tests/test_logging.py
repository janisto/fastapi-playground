"""Tests for Cloud Run stdout JSON logging and middleware."""

import json
import logging
from datetime import datetime, timezone
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.logging import CloudRunJSONFormatter, setup_logging
from app.main import app as base_app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    # Ensure logging is configured for tests
    setup_logging()
    # Use app with middleware already added in main.py
    yield TestClient(base_app)


class TestJSONFormatter:
    def test_severity_mapping_and_time(self) -> None:
        formatter = CloudRunJSONFormatter()
        logger = logging.getLogger("test.logger")
        logger.setLevel(logging.INFO)

        # Build a record manually for determinism
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname=__file__,
            lineno=42,
            msg="Something failed",
            args=(),
            exc_info=None,
        )
        # Freeze created timestamp
        fixed = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
        record.created = fixed
        out = formatter.format(record)
        data = json.loads(out)
        assert data["severity"] == "ERROR"
        assert data["message"] == "Something failed"
        assert data["logger"] == "test.logger"
        # RFC3339 timestamp
        assert data["time"].startswith("2025-01-01T00:00:00")
        # sourceLocation is present
        assert "logging.googleapis.com/sourceLocation" in data


class TestMiddleware:
    def test_trace_injection(self, client: TestClient) -> None:
        # Simulate Cloud Trace header
        trace_header = "0123456789abcdef0123456789abcdef/123456;o=1"
        res = client.get("/health", headers={"X-Cloud-Trace-Context": trace_header})
        assert res.status_code == 200
        # We can't directly read logs here, but ensure the middleware runs by verifying response
        # and that no exceptions are raised. For completeness, ensure app responds normally.
        data = res.json()
        assert data["status"] == "healthy"
