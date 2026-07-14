"""
Unit tests for application logging configuration.
"""

import logging
from collections.abc import Generator
from types import SimpleNamespace

import pytest
from fastapi_request_observability import JSONFormatter, LoggingPreset
from pytest_mock import MockerFixture

from app.core.logging import configure_logging


@pytest.fixture(autouse=True)
def restore_logging_state() -> Generator[None]:
    """
    Restore global logger state after each configuration test.
    """
    import app.core.logging as logging_module

    root = logging.getLogger()
    root_handlers = root.handlers.copy()
    root_level = root.level
    uvicorn_states = {
        name: (logger.handlers.copy(), logger.level, logger.propagate, logger.disabled)
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access")
        if (logger := logging.getLogger(name))
    }
    logging_module._logging_configured = False

    yield

    root.handlers = root_handlers
    root.setLevel(root_level)
    for name, (handlers, level, propagate, disabled) in uvicorn_states.items():
        logger = logging.getLogger(name)
        logger.handlers = handlers
        logger.setLevel(level)
        logger.propagate = propagate
        logger.disabled = disabled
    logging_module._logging_configured = False


def test_configures_gcp_json_formatter(mocker: MockerFixture) -> None:
    """
    Verify application logs use the package's GCP formatter.
    """
    mocker.patch("app.core.logging.get_settings", return_value=SimpleNamespace(log_level="INFO"))

    configure_logging()

    root = logging.getLogger()
    assert root.level == logging.INFO
    assert len(root.handlers) == 1
    formatter = root.handlers[0].formatter
    assert isinstance(formatter, JSONFormatter)
    assert formatter.preset is LoggingPreset.GCP
    assert formatter.include_source is True


def test_uses_configured_log_level(mocker: MockerFixture) -> None:
    """
    Verify the explicit setting controls the application log level.
    """
    mocker.patch("app.core.logging.get_settings", return_value=SimpleNamespace(log_level="DEBUG"))

    configure_logging()

    assert logging.getLogger().level == logging.DEBUG
    assert logging.getLogger("uvicorn.error").level == logging.DEBUG


def test_disables_uvicorn_access_logger(mocker: MockerFixture) -> None:
    """
    Verify Uvicorn does not duplicate package access records.
    """
    mocker.patch("app.core.logging.get_settings", return_value=SimpleNamespace(log_level="INFO"))

    configure_logging()

    access_logger = logging.getLogger("uvicorn.access")
    assert access_logger.disabled is True
    assert access_logger.propagate is False
    assert access_logger.handlers == []


def test_configuration_is_idempotent(mocker: MockerFixture) -> None:
    """
    Verify repeated startup calls do not add handlers.
    """
    mock_get_settings = mocker.patch(
        "app.core.logging.get_settings",
        return_value=SimpleNamespace(log_level="INFO"),
    )

    configure_logging()
    configure_logging()

    assert len(logging.getLogger().handlers) == 1
    mock_get_settings.assert_called_once()
