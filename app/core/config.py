"""Configuration settings for the application."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    environment: str = Field(default="production", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8080, alias="PORT")

    # Firebase
    firebase_project_id: str = Field(default="test-project", alias="FIREBASE_PROJECT_ID")
    firebase_credentials_path: str | None = Field(default=None, alias="GOOGLE_APPLICATION_CREDENTIALS")
    firebase_project_number: str | None = Field(default=None, alias="FIREBASE_PROJECT_NUMBER")

    # App metadata (optional / informational)
    app_environment: str | None = Field(default=None, alias="APP_ENVIRONMENT")
    app_url: str | None = Field(default=None, alias="APP_URL")

    # Secrets
    secret_manager_enabled: bool = Field(default=True, alias="SECRET_MANAGER_ENABLED")

    # Security / Limits
    max_request_size_bytes: int = Field(default=1_000_000, alias="MAX_REQUEST_SIZE_BYTES")
    cors_origins: str | None = Field(default=None, alias="CORS_ORIGINS")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
