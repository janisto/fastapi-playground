"""Shared pytest fixtures and test helpers."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth.firebase import FirebaseUser
from app.main import app
from tests.helpers.auth import make_fake_user, override_current_user


@pytest.fixture
def client() -> Generator[TestClient]:
    """FastAPI TestClient with startup/shutdown and external init patched.

    - Patches Firebase initialization and logging setup to avoid side effects.
    - Yields a TestClient with lifespan management via context manager.
    """
    with patch("app.main.initialize_firebase"), patch("app.main.setup_logging"):
        with TestClient(app) as c:
            yield c


@pytest.fixture
def fake_user() -> FirebaseUser:
    """A simple fake FirebaseUser for auth overrides/tests."""
    return make_fake_user()


@pytest.fixture
def with_fake_user(fake_user: FirebaseUser) -> Generator[None]:
    """Override router current user for the duration of a test using helpers.

    Usage:
        def test_x(client, with_fake_user):
            res = client.get("/profile/")
            ...
    """
    with override_current_user(lambda: fake_user):
        yield
