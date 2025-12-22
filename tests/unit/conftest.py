"""
Unit test fixtures.

Unit tests should not use the `client` fixture (TestClient with real app).
They test isolated functions/classes with mocked dependencies.
"""

from collections.abc import Generator

import pytest

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
