"""
Unit tests for Firebase initialization and configuration.
"""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

import app.core.firebase as firebase_mod
from app.core.firebase import (
    close_async_firestore_client,
    get_async_firestore_client,
    get_firebase_app,
    get_firestore_client,
)


@pytest.fixture(autouse=True)
def reset_global_state() -> Generator[None]:
    """
    Reset global Firebase state before and after each test.
    """
    original_app = firebase_mod._firebase_app
    original_client = firebase_mod._firestore_client
    original_async_client = firebase_mod._async_firestore_client

    firebase_mod._firebase_app = None
    firebase_mod._firestore_client = None
    firebase_mod._async_firestore_client = None

    yield

    firebase_mod._firebase_app = original_app
    firebase_mod._firestore_client = original_client
    firebase_mod._async_firestore_client = original_async_client


class TestGetFirebaseApp:
    """
    Tests for get_firebase_app function.
    """

    def test_raises_when_not_initialized(self) -> None:
        """
        Verify RuntimeError is raised when Firebase is not initialized.
        """
        with pytest.raises(RuntimeError, match="Firebase not initialized"):
            get_firebase_app()

    def test_returns_app_when_initialized(self) -> None:
        """
        Verify app is returned when Firebase is initialized.
        """
        mock_app = MagicMock()
        firebase_mod._firebase_app = mock_app

        result = get_firebase_app()

        assert result is mock_app


class TestGetFirestoreClient:
    """
    Tests for get_firestore_client function.
    """

    def test_raises_when_not_initialized(self) -> None:
        """
        Verify RuntimeError is raised when Firestore client is not available.
        """
        with pytest.raises(RuntimeError, match="Firestore client is not available"):
            get_firestore_client()

    def test_returns_client_when_initialized(self) -> None:
        """
        Verify client is returned when Firestore is initialized.
        """
        mock_client = MagicMock()
        firebase_mod._firestore_client = mock_client

        result = get_firestore_client()

        assert result is mock_client


class TestGetAsyncFirestoreClient:
    """
    Tests for get_async_firestore_client function.
    """

    def test_creates_client_on_first_call(self, mocker: MockerFixture) -> None:
        """
        Verify AsyncClient is created lazily on first call.
        """
        mock_async_client = MagicMock()
        mock_async_client_cls = mocker.patch(
            "app.core.firebase.AsyncClient",
            return_value=mock_async_client,
        )
        mocker.patch(
            "app.core.firebase.get_settings",
            return_value=MagicMock(firebase_project_id="test-project"),
        )

        result = get_async_firestore_client()

        assert result is mock_async_client
        mock_async_client_cls.assert_called_once_with(project="test-project")

    def test_returns_existing_client_on_subsequent_calls(self, mocker: MockerFixture) -> None:
        """
        Verify same client is returned on subsequent calls (singleton).
        """
        mock_async_client = MagicMock()
        firebase_mod._async_firestore_client = mock_async_client

        result = get_async_firestore_client()

        assert result is mock_async_client


class TestCloseAsyncFirestoreClient:
    """
    Tests for close_async_firestore_client function.
    """

    async def test_closes_client_when_exists(self) -> None:
        """
        Verify client is closed and reset to None.
        """
        mock_client = AsyncMock()
        firebase_mod._async_firestore_client = mock_client

        await close_async_firestore_client()

        mock_client.close.assert_awaited_once()
        assert firebase_mod._async_firestore_client is None

    async def test_does_nothing_when_no_client(self) -> None:
        """
        Verify no error when client is None.
        """
        firebase_mod._async_firestore_client = None

        await close_async_firestore_client()

        assert firebase_mod._async_firestore_client is None
