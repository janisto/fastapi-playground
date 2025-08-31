"""Lightweight JSON logging to stdout optimized for Cloud Run.

This module configures Python's logging to emit one-line JSON objects to stdout so
Cloud Run/Cloud Logging can ingest them directly without using the Cloud Logging API.
It avoids in-process buffering and heavy network I/O introduced by API handlers.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, UTC
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings

# Global logging setup flag
_logging_configured = False


# Context: request-scoped trace/span for Cloud Trace correlation
_request_context: ContextVar[dict[str, str]] = ContextVar("request_context", default={})


def _severity_for_level(levelno: int) -> str:
    """Map Python logging level to Cloud Logging severity string."""
    # Cloud severities: DEFAULT, DEBUG, INFO, NOTICE, WARNING, ERROR, CRITICAL, ALERT, EMERGENCY
    if levelno >= logging.CRITICAL:
        return "CRITICAL"
    if levelno >= logging.ERROR:
        return "ERROR"
    if levelno >= logging.WARNING:
        return "WARNING"
    if levelno >= logging.INFO:
        return "INFO"
    if levelno >= logging.DEBUG:
        return "DEBUG"
    return "DEFAULT"


class CloudRunJSONFormatter(logging.Formatter):
    """A minimal, fast JSON formatter for Cloud Run stdout structured logs."""

    def __init__(self, *, include_source: bool = True) -> None:
        super().__init__()
        self.include_source = include_source

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        # Build base payload
        iso_ts = datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="microseconds")
        payload: dict[str, Any] = {
            "severity": _severity_for_level(record.levelno),
            "message": record.getMessage(),
            # Use record.created for perf; convert to RFC3339 with microseconds
            "time": iso_ts,
            "timestamp": iso_ts,
            "logger": record.name,
        }

        # Attach trace/span if available
        ctx = _request_context.get()
        if ctx:
            trace = ctx.get("trace")
            span_id = ctx.get("span_id")
            if trace:
                payload["trace"] = trace
            if span_id:
                payload["spanId"] = span_id

        # Optional source location (helps debugging; small overhead)
        if self.include_source:
            payload["logging.googleapis.com/sourceLocation"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Structured extra fields on the record (skip private/standard fields)
        for key, value in record.__dict__.items():
            if key.startswith("_"):
                continue
            if key in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            }:
                continue
            # Avoid overwriting official keys
            if key in payload:
                continue
            # Coerce None labels to strings to avoid label nesting quirks
            payload[key] = "null" if value is None else value

        # Exceptions as stack string
        if record.exc_info:
            payload["stack"] = self.formatException(record.exc_info)

        # Compact JSON for performance/bandwidth
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class RequestContextLogMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware to propagate Cloud Trace IDs into logs.

    Extracts trace context from the "X-Cloud-Trace-Context" header:
    - Header format: TRACE_ID/SPAN_ID;o=TRACE_TRUE
    - Adds `trace` = projects/<project-id>/traces/<TRACE_ID>
    - Adds `spanId` = <SPAN_ID>
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._project_id = get_settings().gcp_project_id

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        headers = {k.lower(): v for k, v in request.headers.items()}
        header = headers.get("x-cloud-trace-context")
        token = None
        if header:
            # Format: TRACE_ID/SPAN_ID;o=1
            try:
                trace_id_part, rest = header.split("/", 1)
                span_id_part = rest.split(";", 1)[0]
                trace = f"projects/{self._project_id}/traces/{trace_id_part}"
                ctx = {"trace": trace, "span_id": span_id_part}
                token = _request_context.set(ctx)
            except Exception:
                # If parsing fails, ignore and continue
                token = None

        try:
            response = await call_next(request)
            return response
        finally:
            if token is not None:
                # Reset context when request ends
                _request_context.reset(token)


def setup_logging() -> None:
    """Set up logging configuration for stdout JSON logs."""
    global _logging_configured
    if _logging_configured:
        return

    settings = get_settings()

    # Root logger configuration
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG if settings.debug else logging.INFO)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(CloudRunJSONFormatter(include_source=True))
    root.addHandler(handler)

    # Make uvicorn loggers consistent (if running with uvicorn)
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True  # Let them bubble to root JSON handler
        # Keep INFO for access logs even if debug
        if name == "uvicorn.access":
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(root.level)

    _logging_configured = True
    logging.getLogger(__name__).info("Logging configured for Cloud Run stdout")


def get_logger(name: str) -> logging.Logger:
    """Get a module-scoped logger."""
    return logging.getLogger(name)
