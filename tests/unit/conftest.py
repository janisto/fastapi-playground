"""
Unit test fixtures.

Unit tests should not use the `client` fixture (TestClient with real app).
They test isolated functions/classes with mocked dependencies.
"""

import os
from collections.abc import Generator

import pytest

os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "INFO"
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["CORS_ORIGINS"] = ""

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def reset_settings_cache() -> Generator[None]:
    """
    Reset settings cache before and after each unit test.

    Ensures environment variable changes in tests don't leak.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
