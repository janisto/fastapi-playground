"""
Application logging configuration.
"""

import logging
import sys

from fastapi_request_observability import JSONFormatter, LoggingPreset

from app.core.config import get_settings

_logging_configured = False


def configure_logging() -> None:
    """
    Configure structured GCP-compatible logging for the application.
    """
    global _logging_configured
    if _logging_configured:
        return

    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(settings.log_level)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JSONFormatter(LoggingPreset.GCP, include_source=True))
    root.addHandler(handler)

    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(root.level)

    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True

    _logging_configured = True
