"""
Unit tests for configuration settings.
"""

import os
from typing import Any, cast

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings, parse_cors_origins


def _create_settings(**kwargs: Any) -> Settings:  # noqa: ANN401
    """
    Create Settings instance without reading .env file.

    The _env_file parameter is supported by pydantic-settings at runtime
    but not exposed in the type hints, hence the cast.
    """
    if "firebase_project_id" not in kwargs and "FIREBASE_PROJECT_ID" not in os.environ:
        kwargs["firebase_project_id"] = "test-project"
    return cast("Any", Settings)(_env_file=None, **kwargs)


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Clear settings-related environment variables to test defaults.

    This ensures tests are isolated from the .env file and system environment.
    """
    env_vars = [
        "ENVIRONMENT",
        "DEBUG",
        "FIREBASE_PROJECT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "FIRESTORE_DATABASE",
        "MAX_REQUEST_SIZE_BYTES",
        "CORS_ORIGINS",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)


class TestParseCorsOrigins:
    """
    Tests for parse_cors_origins function.
    """

    def test_parses_json_array(self) -> None:
        """
        Verify JSON array is parsed correctly.
        """
        result = parse_cors_origins('["http://localhost:3000", "https://example.com"]')

        assert result == ["http://localhost:3000", "https://example.com"]

    def test_parses_comma_separated(self) -> None:
        """
        Verify comma-separated string is parsed correctly.
        """
        result = parse_cors_origins("http://localhost:3000,https://example.com")

        assert result == ["http://localhost:3000", "https://example.com"]

    def test_strips_whitespace_from_comma_separated(self) -> None:
        """
        Verify whitespace is stripped from comma-separated values.
        """
        result = parse_cors_origins("http://localhost:3000 , https://example.com , http://app.test")

        assert result == ["http://localhost:3000", "https://example.com", "http://app.test"]

    def test_returns_empty_list_for_empty_string(self) -> None:
        """
        Verify empty string returns empty list.
        """
        result = parse_cors_origins("")

        assert result == []

    def test_returns_empty_list_for_whitespace_only(self) -> None:
        """
        Verify whitespace-only string returns empty list.
        """
        result = parse_cors_origins("   ")

        assert result == []

    def test_passes_through_list(self) -> None:
        """
        Verify list input is passed through unchanged.
        """
        origins = ["http://localhost:3000", "https://example.com"]

        result = parse_cors_origins(origins)

        assert result == origins

    @pytest.mark.parametrize("value", ['["https://example.com", 42]', ["https://example.com", 42]])
    def test_rejects_non_string_array_entries(self, value: object) -> None:
        """
        Verify malformed origin arrays cannot be silently stringified.
        """
        with pytest.raises(ValueError, match="entries must be strings"):
            parse_cors_origins(value)

    def test_rejects_non_string_input(self) -> None:
        """
        Verify programmatic settings input uses the same strict contract.
        """
        with pytest.raises(TypeError, match="string or array"):
            parse_cors_origins(42)

    def test_single_value_without_comma(self) -> None:
        """
        Verify single value without comma is parsed correctly.
        """
        result = parse_cors_origins("http://localhost:3000")

        assert result == ["http://localhost:3000"]

    def test_ignores_empty_entries_in_comma_separated(self) -> None:
        """
        Verify empty entries are filtered out.
        """
        result = parse_cors_origins("http://localhost:3000,,https://example.com,")

        assert result == ["http://localhost:3000", "https://example.com"]

    def test_invalid_json_is_rejected(self) -> None:
        """
        Verify invalid JSON starting with an array marker is rejected.
        """
        with pytest.raises(ValueError, match="valid JSON array"):
            parse_cors_origins("[invalid json")

    def test_valid_json_non_list_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify valid JSON that is not a list is rejected.

        This edge case covers when JSON parses successfully but isn't a list.
        """
        # Mock json.loads to return a dict instead of list to test the branch
        monkeypatch.setattr("app.core.config.json.loads", lambda x: {"key": "value"})

        with pytest.raises(ValueError, match="must be an array"):
            parse_cors_origins("[fake json that returns dict]")


class TestSettings:
    """
    Tests for Settings class.
    """

    def test_default_environment(self) -> None:
        """
        Verify default environment is production.
        """
        settings = _create_settings()

        assert settings.environment == "production"

    def test_default_debug(self) -> None:
        """
        Verify debug mode defaults to False for production safety.

        Debug must default to False to ensure:
        - HSTS headers are applied in production
        - Log levels are appropriate (INFO, not DEBUG)
        - No stack traces are exposed to clients
        """
        settings = _create_settings()

        assert settings.debug is False

    def test_firebase_project_id_is_required(self) -> None:
        """
        Verify startup configuration fails without a Firebase project ID.
        """
        with pytest.raises(ValidationError):
            cast("Any", Settings)(_env_file=None)

    def test_default_max_request_size(self) -> None:
        """
        Verify default max request size.
        """
        settings = _create_settings()

        assert settings.max_request_size_bytes == 1_000_000

    def test_default_cors_origins_empty(self) -> None:
        """
        Verify CORS origins defaults to empty list.
        """
        settings = _create_settings()

        assert settings.cors_origins == []


class TestSettingsFromEnv:
    """
    Tests for settings loaded from environment variables.
    """

    def test_environment_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify environment is loaded from env var.
        """
        monkeypatch.setenv("ENVIRONMENT", "development")

        settings = _create_settings()

        assert settings.environment == "development"

    def test_debug_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify debug is loaded from env var.
        """
        monkeypatch.setenv("DEBUG", "false")

        settings = _create_settings()

        assert settings.debug is False

    def test_firebase_project_id_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify Firebase project ID is loaded from env var.
        """
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "my-project")

        settings = _create_settings()

        assert settings.firebase_project_id == "my-project"

    def test_max_request_size_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify max request size is loaded from env var.
        """
        monkeypatch.setenv("MAX_REQUEST_SIZE_BYTES", "2000000")

        settings = _create_settings()

        assert settings.max_request_size_bytes == 2_000_000

    def test_cors_origins_from_env_json_array(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify CORS origins is loaded from JSON array env var.
        """
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000", "https://example.com"]')

        settings = _create_settings()

        assert settings.cors_origins == ["http://localhost:3000", "https://example.com"]

    def test_cors_origins_from_env_comma_separated(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify CORS origins is loaded from comma-separated env var.
        """
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,https://example.com")

        settings = _create_settings()

        assert settings.cors_origins == ["http://localhost:3000", "https://example.com"]

    def test_cors_origins_comma_separated_with_spaces(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify CORS origins handles comma-separated values with spaces.
        """
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://example.com , http://app.test")

        settings = _create_settings()

        assert settings.cors_origins == ["http://localhost:3000", "https://example.com", "http://app.test"]

    def test_cors_origins_single_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify CORS origins handles single value without comma.
        """
        monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

        settings = _create_settings()

        assert settings.cors_origins == ["http://localhost:3000"]

    def test_cors_origins_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify CORS origins handles empty string.
        """
        monkeypatch.setenv("CORS_ORIGINS", "")

        settings = _create_settings()

        assert settings.cors_origins == []

    def test_google_credentials_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify Google credentials path is loaded from env var.
        """
        monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/creds.json")

        settings = _create_settings()

        assert settings.google_application_credentials == "/path/to/creds.json"

    def test_case_insensitive_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify env vars are case insensitive.
        """
        monkeypatch.setenv("environment", "test")

        settings = _create_settings()

        assert settings.environment == "test"

    def test_invalid_environment_is_rejected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unknown environment names cannot disable production safeguards silently."""
        monkeypatch.setenv("ENVIRONMENT", "prodution")

        with pytest.raises(ValidationError):
            _create_settings()

    def test_non_positive_request_size_is_rejected(self) -> None:
        """Request size limits must be strictly positive."""
        with pytest.raises(ValidationError):
            _create_settings(max_request_size_bytes=0)


class TestSettingsIgnoreExtra:
    """
    Tests for extra fields handling.
    """

    def test_ignores_unknown_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Verify unknown env vars are ignored.
        """
        monkeypatch.setenv("UNKNOWN_SETTING", "value")

        settings = _create_settings()

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
        settings = _create_settings()

        assert settings.google_application_credentials is None

    def test_firestore_database_default_none(self) -> None:
        """
        Verify Firestore database defaults to None (uses default database).
        """
        settings = _create_settings()

        assert settings.firestore_database is None
