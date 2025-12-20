from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from app.core import firebase


@pytest.fixture(autouse=True)
def reset_singletons() -> Generator[None]:
    firebase._firebase_app = None
    firebase._firestore_client = None
    yield
    firebase._firebase_app = None
    firebase._firestore_client = None


def test_initialize_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = MagicMock()
    settings.firebase_credentials_path = None
    settings.firebase_project_id = "pid"
    monkeypatch.setattr("app.core.firebase.get_settings", lambda: settings)
    mock_app = MagicMock()
    mock_firestore_client = MagicMock()

    with (
        patch("firebase_admin.initialize_app", return_value=mock_app) as init_app,
        patch("firebase_admin.firestore.client", return_value=mock_firestore_client),
    ):
        firebase.initialize_firebase()
        assert firebase.get_firebase_app() is mock_app
        assert firebase.get_firestore_client() is mock_firestore_client
        # Second call should be no-op
        firebase.initialize_firebase()
        init_app.assert_called_once()


def test_get_firestore_client_uninitialized() -> None:
    with pytest.raises(RuntimeError):
        firebase.get_firestore_client()


def test_get_firebase_app_uninitialized() -> None:
    with pytest.raises(RuntimeError):
        firebase.get_firebase_app()
