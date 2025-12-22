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

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

FIRESTORE_HOST = "127.0.0.1:7030"
AUTH_HOST = "127.0.0.1:7010"
PROJECT_ID = "demo-test"


def _emulator_running(host: str) -> bool:
    """
    Check if an emulator is running at the given host.
    """
    try:
        httpx.get(f"http://{host}/", timeout=1.0)
        return True
    except httpx.RequestError:
        return False


@pytest.fixture(scope="session", autouse=True)
def require_emulators() -> None:
    """
    Skip all E2E tests if emulators are not running.

    Sets environment variables for emulator hosts.
    """
    if not _emulator_running(FIRESTORE_HOST):
        pytest.skip("Firebase emulators not running (run: just emulators)")

    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_HOST
    os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = AUTH_HOST


@pytest.fixture(autouse=True)
def clear_emulator_data() -> Generator[None]:
    """
    Clear Firestore emulator data after each test.

    Ensures test isolation by removing all documents.
    """
    yield
    with contextlib.suppress(httpx.RequestError):
        httpx.delete(
            f"http://{FIRESTORE_HOST}/emulator/v1/projects/{PROJECT_ID}/databases/(default)/documents",
            timeout=5.0,
        )


@pytest.fixture
def e2e_client() -> Generator[TestClient]:
    """
    TestClient for E2E tests against real emulators.

    Unlike integration tests, this does NOT mock Firebase/Firestore.
    """
    with TestClient(app) as c:
        yield c
