"""
E2E test fixtures for Firebase emulator integration.

These tests require Firebase emulators to be running:
    firebase emulators:start --only auth,firestore

Or using just:
    just emulators
"""

import contextlib
import os
from collections.abc import Generator

import httpx2
import pytest
from fastapi.testclient import TestClient

FIRESTORE_HOST = "127.0.0.1:7030"
AUTH_HOST = "127.0.0.1:7010"
PROJECT_ID = "demo-test"

os.environ.setdefault("FIRESTORE_EMULATOR_HOST", FIRESTORE_HOST)
os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", AUTH_HOST)
os.environ.setdefault("FIREBASE_PROJECT_ID", PROJECT_ID)

# App imports must follow emulator configuration because settings are resolved during import.
from app.auth.firebase import FirebaseUser, verify_firebase_token  # noqa: E402
from app.main import app, fastapi_app  # noqa: E402


def _emulator_running(host: str) -> bool:
    """
    Check if an emulator is running at the given host.
    """
    try:
        httpx2.get(f"http://{host}/", timeout=1.0)
        return True
    except httpx2.RequestError:
        return False


@pytest.fixture(scope="session", autouse=True)
def require_emulators() -> None:
    """
    Skip all E2E tests if emulators are not running.

    Sets environment variables for emulator hosts.
    """
    if not _emulator_running(FIRESTORE_HOST):
        pytest.skip("Firebase emulators not running (run: just emulators)")


@pytest.fixture(autouse=True)
def clear_emulator_data() -> Generator[None]:
    """
    Clear Firestore emulator data after each test.

    Ensures test isolation by removing all documents.
    """
    yield
    with contextlib.suppress(httpx2.RequestError):
        httpx2.delete(
            f"http://{FIRESTORE_HOST}/emulator/v1/projects/{PROJECT_ID}/databases/(default)/documents",
            timeout=5.0,
        )


@pytest.fixture
def e2e_client() -> Generator[TestClient]:
    """
    TestClient for E2E tests against real emulators.

    Unlike integration tests, this does NOT mock Firebase/Firestore.
    """

    async def authenticated_user() -> FirebaseUser:
        return FirebaseUser(uid="e2e-user", email="e2e@example.com", email_verified=True)

    fastapi_app.dependency_overrides[verify_firebase_token] = authenticated_user
    try:
        with TestClient(app) as client:
            yield client
    finally:
        fastapi_app.dependency_overrides.pop(verify_firebase_token, None)
