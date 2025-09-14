import json
import logging
from io import StringIO

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.core import logging as app_logging


def test_severity_for_level_mapping() -> None:
    m = app_logging._severity_for_level  # type: ignore[attr-defined]
    assert m(logging.CRITICAL) == "CRITICAL"
    assert m(logging.ERROR) == "ERROR"
    assert m(logging.WARNING) == "WARNING"
    assert m(logging.INFO) == "INFO"
    assert m(logging.DEBUG) == "DEBUG"
    # Below DEBUG
    assert m(1) == "DEFAULT"


def test_formatter_basic_and_source_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello %s",
        args=("world",),
        exc_info=None,
        func="func",
    )
    fmt_with = app_logging.CloudRunJSONFormatter(include_source=True)
    out_with = json.loads(fmt_with.format(record))
    assert out_with["message"] == "hello world"
    assert "logging.googleapis.com/sourceLocation" in out_with

    fmt_without = app_logging.CloudRunJSONFormatter(include_source=False)
    out_without = json.loads(fmt_without.format(record))
    assert "logging.googleapis.com/sourceLocation" not in out_without


def test_formatter_includes_extra_and_exception() -> None:
    # Capture real exc_info via sys.exc_info() pattern
    try:
        raise RuntimeError("stack")
    except RuntimeError:
        import sys

        exc_info = sys.exc_info()
    record2 = logging.LogRecord(
        name="svc",
        level=logging.ERROR,
        pathname=__file__,
        lineno=55,
        msg="with extra",
        args=(),
        exc_info=exc_info,
        func="y",
    )
    # Add extra custom field
    setattr(record2, "user_id", "u123")
    formatter = app_logging.CloudRunJSONFormatter()
    payload = json.loads(formatter.format(record2))
    assert payload["severity"] == "ERROR"
    assert payload["user_id"] == "u123"
    assert "stack" in payload


def test_request_context_middleware_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    app_logging._request_context.set({})  # type: ignore[attr-defined]

    app = FastAPI()

    # Attach middleware
    app.add_middleware(app_logging.RequestContextLogMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:  # type: ignore[override]
        # Inside handler, context var should be populated if header parsed
        ctx = app_logging._request_context.get()  # type: ignore[attr-defined]
        return {"has_trace": str("trace" in ctx), "has_span": str("span_id" in ctx)}

    client = TestClient(app)
    trace_header = "abcd1234/00000001;o=1"
    r = client.get("/ping", headers={"X-Cloud-Trace-Context": trace_header})
    assert r.status_code == 200
    assert r.json()["has_trace"] == "True"
    assert r.json()["has_span"] == "True"

    # Ensure context resets after request (new request w/out header)
    r2 = client.get("/ping")
    assert r2.json()["has_trace"] == "False"


def test_setup_logging_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    # Reset module flag/state safely
    app_logging._logging_configured = False  # type: ignore[attr-defined]
    stream = StringIO()

    class DummyStreamHandler(logging.StreamHandler):
        def __init__(self) -> None:  # pragma: no cover - trivial
            super().__init__(stream)

    # Patch StreamHandler used in setup to capture output
    monkeypatch.setattr(app_logging, "logging", logging)
    monkeypatch.setattr(app_logging, "sys", type("_S", (), {"stdout": stream}))

    app_logging.setup_logging()
    first_handlers = list(logging.getLogger().handlers)
    app_logging.setup_logging()  # should not add another handler
    second_handlers = list(logging.getLogger().handlers)
    assert first_handlers == second_handlers
    # Basic sanity: JSON line present
    stream.seek(0)
    logged = stream.getvalue().strip().splitlines()
    assert any("Logging configured" in line for line in logged)
