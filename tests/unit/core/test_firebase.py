"""
Unit tests for Firebase initialization and configuration.
"""

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

import app.core.firebase as firebase_mod
from app.core.firebase import (
    close_async_firestore_client,
    get_async_firestore_client,
    get_firebase_app,
    initialize_firebase,
)


@pytest.fixture(autouse=True)
def reset_global_state() -> Generator[None]:
    """
    Reset global Firebase state before and after each test.
    """
    original_app = firebase_mod._firebase_app
    original_async_client = firebase_mod._async_firestore_client

    firebase_mod._firebase_app = None
    firebase_mod._async_firestore_client = None

    yield

    firebase_mod._firebase_app = original_app
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


class TestInitializeFirebase:
    """
    Tests for initialize_firebase.
    """

    def test_adc_initialization_uses_configured_project(self, mocker: MockerFixture) -> None:
        """
        Verify the Firebase app project does not depend on the active gcloud default.
        """
        app = MagicMock()
        initialize_app = mocker.patch("app.core.firebase.firebase_admin.initialize_app", return_value=app)
        mocker.patch(
            "app.core.firebase.get_settings",
            return_value=MagicMock(firebase_project_id="configured-project", google_application_credentials=None),
        )

        initialize_firebase()

        initialize_app.assert_called_once_with(options={"projectId": "configured-project"})
        assert firebase_mod._firebase_app is app

    def test_explicit_credentials_use_configured_project(self, mocker: MockerFixture) -> None:
        """
        Verify service-account initialization retains the configured project boundary.
        """
        credential = MagicMock()
        app = MagicMock()
        certificate = mocker.patch("app.core.firebase.credentials.Certificate", return_value=credential)
        initialize_app = mocker.patch("app.core.firebase.firebase_admin.initialize_app", return_value=app)
        mocker.patch(
            "app.core.firebase.get_settings",
            return_value=MagicMock(
                firebase_project_id="configured-project",
                google_application_credentials="/credentials/service-account.json",
            ),
        )

        initialize_firebase()

        certificate.assert_called_once_with("/credentials/service-account.json")
        initialize_app.assert_called_once_with(credential, {"projectId": "configured-project"})
        assert firebase_mod._firebase_app is app

    def test_existing_app_is_not_reinitialized(self, mocker: MockerFixture) -> None:
        """
        Verify repeated startup calls preserve the existing Firebase app.
        """
        firebase_mod._firebase_app = MagicMock()
        initialize_app = mocker.patch("app.core.firebase.firebase_admin.initialize_app")

        initialize_firebase()

        initialize_app.assert_not_called()

    def test_initialization_failure_is_reraised(self, mocker: MockerFixture) -> None:
        """
        Verify startup fails rather than running with an unusable Firebase app.
        """
        mocker.patch(
            "app.core.firebase.get_settings",
            return_value=MagicMock(firebase_project_id="configured-project", google_application_credentials=None),
        )
        mocker.patch("app.core.firebase.firebase_admin.initialize_app", side_effect=RuntimeError("ADC unavailable"))

        with pytest.raises(RuntimeError, match="ADC unavailable"):
            initialize_firebase()


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
            return_value=MagicMock(firebase_project_id="test-project", firestore_database=None),
        )

        result = get_async_firestore_client()

        assert result is mock_async_client
        mock_async_client_cls.assert_called_once_with(project="test-project", database=None)

    def test_creates_client_with_custom_database(self, mocker: MockerFixture) -> None:
        """
        Verify AsyncClient is created with custom database when configured.
        """
        mock_async_client = MagicMock()
        mock_async_client_cls = mocker.patch(
            "app.core.firebase.AsyncClient",
            return_value=mock_async_client,
        )
        mocker.patch(
            "app.core.firebase.get_settings",
            return_value=MagicMock(firebase_project_id="test-project", firestore_database="custom-db"),
        )

        result = get_async_firestore_client()

        assert result is mock_async_client
        mock_async_client_cls.assert_called_once_with(project="test-project", database="custom-db")

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

    def test_closes_client_when_exists(self) -> None:
        """
        Verify client is closed and reset to None.
        """
        mock_client = MagicMock()
        firebase_mod._async_firestore_client = mock_client

        close_async_firestore_client()

        mock_client.close.assert_called_once_with()
        assert firebase_mod._async_firestore_client is None

    def test_does_nothing_when_no_client(self) -> None:
        """
        Verify no error when client is None.
        """
        firebase_mod._async_firestore_client = None

        close_async_firestore_client()

        assert firebase_mod._async_firestore_client is None
