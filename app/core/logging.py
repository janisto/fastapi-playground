"""Logging configuration using Google Cloud Logging."""

import logging
import sys

from app.core.config import get_settings

# Global logging setup flag
_logging_configured = False


def setup_logging() -> None:
    """Set up logging configuration."""
    global _logging_configured

    if _logging_configured:
        return

    settings = get_settings()

    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Try to set up Google Cloud Logging if available
    if settings.environment == "production":
        try:
            from google.cloud import logging as cloud_logging

            client = cloud_logging.Client()
            client.setup_logging()

            logging.info("Google Cloud Logging configured")
        except Exception as e:
            logging.warning(f"Failed to configure Google Cloud Logging: {e}")

    _logging_configured = True
    logging.info("Logging configured successfully")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
