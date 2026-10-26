"""
Unit tests for Firebase initialization and configuration.
"""

import logging
from collections.abc import Generator
from typing import Literal
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
def reset_global_state(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:
    """
    Reset global Firebase state before and after each test.
    """
    monkeypatch.delenv("FIREBASE_AUTH_EMULATOR_HOST", raising=False)
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
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

    def test_initializes_lazily_when_not_initialized(self, mocker: MockerFixture) -> None:
        """
        Verify protected operations initialize Firebase without gating public startup.
        """
        app = MagicMock()
        initialize = mocker.patch("app.core.firebase.initialize_firebase")

        def install() -> None:
            firebase_mod._firebase_app = app

        initialize.side_effect = install
        assert get_firebase_app() is app
        initialize.assert_called_once_with()

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

    def test_missing_project_fails_only_at_firebase_boundary_without_sensitive_log(
        self,
        mocker: MockerFixture,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mocker.patch(
            "app.core.firebase.get_settings",
            return_value=MagicMock(firebase_project_id=None, google_application_credentials="credential-secret"),
        )
        with (
            caplog.at_level(logging.ERROR, logger="app.core.firebase"),
            pytest.raises(
                RuntimeError,
                match="not configured",
            ),
        ):
            initialize_firebase()

        assert "credential-secret" not in caplog.text
        assert caplog.records[-1].getMessage() == "Firebase initialization failed"


class TestGetAsyncFirestoreClient:
    """
    Tests for get_async_firestore_client function.
    """

    def test_creates_client_on_first_call(self, mocker: MockerFixture) -> None:
        """
        Verify the Admin SDK client uses the initialized app.
        """
        app = MagicMock()
        firebase_mod._firebase_app = app
        mock_async_client = MagicMock()
        client_factory = mocker.patch(
            "app.core.firebase.firestore_async.client",
            return_value=mock_async_client,
        )
        mocker.patch(
            "app.core.firebase.get_settings",
            return_value=MagicMock(firebase_project_id="test-project", firestore_database=None),
        )

        result = get_async_firestore_client()

        assert result is mock_async_client
        client_factory.assert_called_once_with(app=app, database_id=None)

    def test_creates_client_with_custom_database(self, mocker: MockerFixture) -> None:
        """
        Verify AsyncClient is created with custom database when configured.
        """
        app = MagicMock()
        firebase_mod._firebase_app = app
        mock_async_client = MagicMock()
        client_factory = mocker.patch(
            "app.core.firebase.firestore_async.client",
            return_value=mock_async_client,
        )
        mocker.patch(
            "app.core.firebase.get_settings",
            return_value=MagicMock(firebase_project_id="test-project", firestore_database="custom-db"),
        )

        result = get_async_firestore_client()

        assert result is mock_async_client
        client_factory.assert_called_once_with(app=app, database_id="custom-db")

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


@pytest.mark.parametrize(
    ("auth_host", "firestore_host", "environment", "project"),
    [
        ("127.0.0.1:7010", "127.0.0.1:7030", "production", "demo-test"),
        ("127.0.0.1:7010", "127.0.0.1:7030", "test", "real-project"),
        (None, "127.0.0.1:7030", "test", "demo-test"),
        ("127.0.0.1:7010", None, "test", "demo-test"),
        ("", "127.0.0.1:7030", "test", "demo-test"),
        ("example.test:7010", "127.0.0.1:7030", "test", "demo-test"),
        ("127.0.0.1:7010", "192.0.2.1:7030", "test", "demo-test"),
        ("localhost:7010", "localhost.example.test:7030", "test", "demo-test"),
        ("http://127.0.0.1:7010", "127.0.0.1:7030", "test", "demo-test"),
        ("127.0.0.1:7010/path", "127.0.0.1:7030", "test", "demo-test"),
        ("user@127.0.0.1:7010", "127.0.0.1:7030", "test", "demo-test"),
        ("127.0.0.1:7010?secret", "127.0.0.1:7030", "test", "demo-test"),
        ("127.0.0.1:7010#fragment", "127.0.0.1:7030", "test", "demo-test"),
        ("127.0.0.1", "127.0.0.1:7030", "test", "demo-test"),
        ("127.0.0.1:0", "127.0.0.1:7030", "test", "demo-test"),
        ("127.0.0.1:65536", "127.0.0.1:7030", "test", "demo-test"),
    ],
)
def test_unsafe_or_incomplete_emulators_fail_before_credentials_or_sdk_initialization(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    auth_host: str | None,
    firestore_host: str | None,
    environment: Literal["test", "production"],
    project: str,
) -> None:
    from app.core.config import Settings

    for name, value in (("FIREBASE_AUTH_EMULATOR_HOST", auth_host), ("FIRESTORE_EMULATOR_HOST", firestore_host)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    mocker.patch(
        "app.core.firebase.get_settings",
        return_value=Settings(
            _env_file=None,
            environment=environment,
            firebase_project_id=project,
            google_application_credentials="obsolete-key.json",
        ),
    )
    initialize = mocker.patch("app.core.firebase.firebase_admin.initialize_app")
    certificate = mocker.patch("app.core.firebase.credentials.Certificate")
    with pytest.raises(ValueError, match="paired loopback"):
        initialize_firebase()
    initialize.assert_not_called()
    certificate.assert_not_called()
    assert firebase_mod._firebase_app is None


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "[::1]"])
def test_local_demo_uses_real_sdk_anonymous_credentials_without_adc(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, host: str
) -> None:
    import firebase_admin
    from google.auth.credentials import AnonymousCredentials

    from app.core.config import Settings

    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", f"{host}:7010")
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", f"{host}:7030")
    mocker.patch(
        "app.core.firebase.get_settings",
        return_value=Settings(
            _env_file=None,
            environment="test",
            firebase_project_id="demo-test",
            google_application_credentials="obsolete-key.json",
        ),
    )
    adc = mocker.patch("google.auth.default", side_effect=AssertionError("ADC lookup"))
    certificate = mocker.patch(
        "app.core.firebase.credentials.Certificate", side_effect=AssertionError("credential file")
    )
    initialize_firebase()
    firebase_app = get_firebase_app()
    try:
        assert firebase_app.project_id == "demo-test"
        assert isinstance(firebase_app.credential.get_credential(), AnonymousCredentials)
        firestore = get_async_firestore_client()
        assert firestore.project == "demo-test"
        assert isinstance(firestore._credentials, AnonymousCredentials)
        adc.assert_not_called()
        certificate.assert_not_called()
    finally:
        close_async_firestore_client()
        firebase_admin.delete_app(firebase_app)
