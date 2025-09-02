"""Tests for Cloud Run stdout JSON logging formatter."""

import json
import logging
from datetime import UTC, datetime

from app.core.logging import CloudRunJSONFormatter


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
        fixed = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC).timestamp()
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
