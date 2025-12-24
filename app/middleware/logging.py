"""
Lightweight JSON logging to stdout optimized for Cloud Run.

This module configures Python's logging to emit one-line JSON objects to stdout so
Cloud Run/Cloud Logging can ingest them directly without using the Cloud Logging API.
It avoids in-process buffering and heavy network I/O introduced by API handlers.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings

# Global logging setup flag
_logging_configured = False


# Context: request-scoped trace/span for Cloud Trace correlation
_request_context: ContextVar[dict[str, str] | None] = ContextVar("request_context", default=None)


def _severity_for_level(levelno: int) -> str:
    """
    Map Python logging level to Cloud Logging severity string.
    """
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
    """
    A minimal, fast JSON formatter for Cloud Run stdout structured logs.
    """

    # Standard LogRecord fields to exclude from extra data (class-level constant for performance)
    _EXCLUDED_FIELDS: frozenset[str] = frozenset(
        {
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
            "message",
            "taskName",
        }
    )

    def __init__(self, *, include_source: bool = True) -> None:
        super().__init__()
        self.include_source = include_source

    def format(self, record: logging.LogRecord) -> str:
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

        # Attach request context if available (trace, span, request_id)
        ctx = _request_context.get()
        if ctx:
            trace = ctx.get("trace")
            span_id = ctx.get("span_id")
            request_id = ctx.get("request_id")
            if trace:
                payload["trace"] = trace
            if span_id:
                payload["spanId"] = span_id
            if request_id:
                payload["request_id"] = request_id

        # Optional source location (helps debugging; small overhead)
        if self.include_source:
            payload["logging.googleapis.com/sourceLocation"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        # Structured extra fields on the record (skip private/standard fields)
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in self._EXCLUDED_FIELDS or key in payload:
                continue
            # Coerce None labels to strings to avoid label nesting quirks
            payload[key] = "null" if value is None else value

        # Exceptions as stack string
        if record.exc_info:
            payload["stack"] = self.formatException(record.exc_info)

        # Compact JSON for performance/bandwidth
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


class RequestContextLogMiddleware(BaseHTTPMiddleware):
    """
    Starlette/FastAPI middleware to propagate request context into logs.

    Handles:
    1. Cloud Trace correlation via "X-Cloud-Trace-Context" header:
       - Header format: TRACE_ID/SPAN_ID;o=TRACE_TRUE
       - Adds `trace` = projects/<project-id>/traces/<TRACE_ID>
       - Adds `spanId` = <SPAN_ID>

    2. Request ID for client traceability:
       - Uses incoming "X-Request-ID" header if present, otherwise generates UUID
       - Adds request_id to all logs during request lifecycle
       - Returns "X-Request-ID" header in response for client reference
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        # Reuse firebase_project_id for trace correlation
        self._project_id = get_settings().firebase_project_id

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        headers = {k.lower(): v for k, v in request.headers.items()}

        # Build request context
        ctx: dict[str, str] = {}

        # Extract or generate request ID for client traceability
        request_id = headers.get("x-request-id") or str(uuid.uuid4())
        ctx["request_id"] = request_id

        # Parse Cloud Trace header if present
        trace_header = headers.get("x-cloud-trace-context")
        if trace_header:
            # Format: TRACE_ID/SPAN_ID;o=1
            parts = trace_header.split("/", 1)
            if len(parts) == 2:
                trace_id_part = parts[0]
                span_id_part = parts[1].split(";", 1)[0]
                ctx["trace"] = f"projects/{self._project_id}/traces/{trace_id_part}"
                ctx["span_id"] = span_id_part

        token = _request_context.set(ctx)
        try:
            response = await call_next(request)
            # Add request ID to response for client reference
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            _request_context.reset(token)


def setup_logging() -> None:
    """
    Set up logging configuration for stdout JSON logs.
    """
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
    """
    Get a module-scoped logger.
    """
    return logging.getLogger(name)


def log_audit_event(
    action: str,
    user_id: str,
    resource_type: str,
    resource_id: str,
    result: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """
    Log an audit event with structured data for Cloud Logging.

    Args:
        action: The action performed (e.g., "create", "update", "delete")
        user_id: The user performing the action
        resource_type: The type of resource (e.g., "profile")
        resource_id: The ID of the resource
        result: The result of the action ("success" or "failure")
        details: Optional additional details
    """
    logger = logging.getLogger(__name__)
    logger.info(
        "Audit event",
        extra={
            "audit": {
                "action": action,
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "result": result,
                "details": details or {},
            }
        },
    )
