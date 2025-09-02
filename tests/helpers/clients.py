"""Client utilities for tests."""

from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


@contextmanager
def test_client() -> Generator[TestClient]:
    """Context-managed TestClient with Firebase/logging init patched.

    Prefer using the shared `client` fixture from tests/conftest.py in most tests.
    """
    with patch("app.main.initialize_firebase"), patch("app.main.setup_logging"):
        with TestClient(app) as c:
            yield c
