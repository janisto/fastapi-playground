"""
Unit tests for configuration settings.
"""

import pytest

from app.core.config import Settings, get_settings


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Clear settings-related environment variables to test defaults.

    This ensures tests are isolated from the .env file and system environment.
    """
    env_vars = [
        "ENVIRONMENT",
        "DEBUG",
        "HOST",
        "PORT",
        "FIREBASE_PROJECT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "FIREBASE_PROJECT_NUMBER",
        "FIRESTORE_DATABASE",
        "APP_ENVIRONMENT",
        "APP_URL",
        "SECRET_MANAGER_ENABLED",
        "MAX_REQUEST_SIZE_BYTES",
        "CORS_ORIGINS",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


class TestSettings:
    """
    Tests for Settings class.
    """

    def test_default_environment(self) -> None:
        """
        Verify default environment is production.
        """
        settings = Settings(_env_file=None)

        assert settings.environment == "production"

    def test_default_debug(self) -> None:
        """
        Verify debug mode defaults to False for production safety.

        Debug must default to False to ensure:
        - HSTS headers are applied in production
        - Log levels are appropriate (INFO, not DEBUG)
        - No stack traces are exposed to clients
        """
        settings = Settings(_env_file=None)

        assert settings.debug is False

    def test_default_host(self) -> None:
        """
        Verify default host.
        """
        settings = Settings(_env_file=None)

        assert settings.host == "0.0.0.0"

    def test_default_port(self) -> None:
        """
        Verify default port.
        """
        settings = Settings(_env_file=None)

        assert settings.port == 8080

    def test_default_firebase_project_id(self) -> None:
        """
        Verify default Firebase project ID.
        """
        settings = Settings(_env_file=None)

        assert settings.firebase_project_id == "test-project"

    def test_default_max_request_size(self) -> None:
        """
        Verify default max request size.
        """
        settings = Settings(_env_file=None)

        assert settings.max_request_size_bytes == 1_000_000

    def test_default_cors_origins_empty(self) -> None:
        """
        Verify CORS origins defaults to empty list.
        """
        settings = Settings(_env_file=None)

        assert settings.cors_origins == []

    def test_default_secret_manager_enabled(self) -> None:
        """
        Verify Secret Manager is enabled by default.
        """
        settings = Settings(_env_file=None)

        assert settings.secret_manager_enabled is True


class TestSettingsFromEnv:
    """
    Tests for settings loaded from environment variables.
    """

    def test_environment_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify environment is loaded from env var.
        """
        monkeypatch.setenv("ENVIRONMENT", "development")

        settings = Settings(_env_file=None)

        assert settings.environment == "development"

    def test_debug_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify debug is loaded from env var.
        """
        monkeypatch.setenv("DEBUG", "false")

        settings = Settings(_env_file=None)

        assert settings.debug is False

    def test_port_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify port is loaded from env var.
        """
        monkeypatch.setenv("PORT", "9000")

        settings = Settings(_env_file=None)

        assert settings.port == 9000

    def test_firebase_project_id_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify Firebase project ID is loaded from env var.
        """
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "my-project")

        settings = Settings(_env_file=None)

        assert settings.firebase_project_id == "my-project"

    def test_max_request_size_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify max request size is loaded from env var.
        """
        monkeypatch.setenv("MAX_REQUEST_SIZE_BYTES", "2000000")

        settings = Settings(_env_file=None)

        assert settings.max_request_size_bytes == 2_000_000

    def test_cors_origins_from_env_json_array(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify CORS origins is loaded from JSON array env var.
        """
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000", "https://example.com"]')

        settings = Settings(_env_file=None)

        assert settings.cors_origins == ["http://localhost:3000", "https://example.com"]

    def test_google_credentials_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify Google credentials path is loaded from env var.
        """
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/creds.json")

        settings = Settings(_env_file=None)

        assert settings.google_application_credentials == "/path/to/creds.json"

    def test_case_insensitive_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify env vars are case insensitive.
        """
        monkeypatch.setenv("environment", "staging")

        settings = Settings(_env_file=None)

        assert settings.environment == "staging"


class TestSettingsIgnoreExtra:
    """
    Tests for extra fields handling.
    """

    def test_ignores_unknown_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify unknown env vars are ignored.
        """
        monkeypatch.setenv("UNKNOWN_SETTING", "value")

        settings = Settings(_env_file=None)

        assert not hasattr(settings, "unknown_setting")


class TestGetSettings:
    """
    Tests for get_settings function.
    """

    def test_returns_settings_instance(self) -> None:
        """
        Verify get_settings returns Settings instance.
        """
        get_settings.cache_clear()

        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_returns_cached_instance(self) -> None:
        """
        Verify get_settings returns the same cached instance.
        """
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_cache_clear_creates_new_instance(self) -> None:
        """
        Verify cache_clear creates a new settings instance.
        """
        get_settings.cache_clear()
        settings1 = get_settings()

        get_settings.cache_clear()
        settings2 = get_settings()

        assert settings1 is not settings2


class TestSettingsOptionalFields:
    """
    Tests for optional settings fields.
    """

    def test_google_credentials_default_none(self) -> None:
        """
        Verify Google credentials defaults to None.
        """
        settings = Settings(_env_file=None)

        assert settings.google_application_credentials is None

    def test_firebase_project_number_default_none(self) -> None:
        """
        Verify Firebase project number defaults to None.
        """
        settings = Settings(_env_file=None)

        assert settings.firebase_project_number is None

    def test_firestore_database_default_none(self) -> None:
        """
        Verify Firestore database defaults to None (uses default database).
        """
        settings = Settings(_env_file=None)

        assert settings.firestore_database is None

    def test_app_environment_default_none(self) -> None:
        """
        Verify app environment defaults to None.
        """
        settings = Settings(_env_file=None)

        assert settings.app_environment is None

    def test_app_url_default_none(self) -> None:
        """
        Verify app URL defaults to None.
        """
        settings = Settings(_env_file=None)

        assert settings.app_url is None

    def test_optional_fields_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify optional fields can be set from env.
        """
        monkeypatch.setenv("APP_ENVIRONMENT", "production")
        monkeypatch.setenv("APP_URL", "https://api.example.com")
        monkeypatch.setenv("FIREBASE_PROJECT_NUMBER", "123456789")

        settings = Settings(_env_file=None)

        assert settings.app_environment == "production"
        assert settings.app_url == "https://api.example.com"
        assert settings.firebase_project_number == "123456789"
