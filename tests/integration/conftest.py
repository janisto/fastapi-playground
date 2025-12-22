"""
Integration test fixtures.

Integration tests use the `client` fixture with mocked services
(no Firebase/Firestore). This is the key fixture setup for fast integration tests.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.firebase import FirebaseUser, verify_firebase_token
from app.dependencies import get_profile_service
from app.services.profile import ProfileService
from tests.helpers.auth import make_fake_user


@pytest.fixture
def mock_profile_service() -> AsyncMock:
    """
    Mocked ProfileService for integration tests.
    """
    return AsyncMock(spec=ProfileService)


@pytest.fixture
def client(mock_profile_service: AsyncMock) -> Generator[TestClient]:
    """
    TestClient with mocked services (no Firebase/Firestore).

    - Imports app inside fixture to get current module state (avoids stale references
      if other tests delete/reimport app.main).
    - Patches Firebase initialization to avoid real connections.
    - Injects mock_profile_service via dependency_overrides.
    - Clears all overrides after the test.
    """
    from app.main import app

    with (
        patch("app.main.initialize_firebase"),
        patch("app.main.setup_logging"),
        patch("app.main.close_async_firestore_client"),
    ):
        app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


@pytest.fixture
def fake_user() -> FirebaseUser:
    """
    Fake authenticated user.
    """
    return make_fake_user()


@pytest.fixture
def with_fake_user(fake_user: FirebaseUser) -> Generator[None]:
    """
    Override auth to return fake user.
    """
    from app.main import app

    app.dependency_overrides[verify_firebase_token] = lambda: fake_user
    yield
    app.dependency_overrides.pop(verify_firebase_token, None)
