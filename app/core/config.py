"""
Configuration settings for the application.
"""

from functools import cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.
    """

    # Environment
    environment: str = Field(default="production", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")

    # Firebase
    firebase_project_id: str = Field(default="test-project", description="Firebase project ID")
    google_application_credentials: str | None = Field(default=None, description="Path to service account credentials")
    firebase_project_number: str | None = Field(default=None, description="Firebase project number")
    firestore_database: str | None = Field(default=None, description="Firestore database ID (default: (default))")

    # App metadata (optional / informational)
    app_environment: str | None = Field(default=None, description="Application environment")
    app_url: str | None = Field(default=None, description="Application URL")

    # Secrets
    secret_manager_enabled: bool = Field(default=True, description="Enable Secret Manager")

    # Security / Limits
    max_request_size_bytes: int = Field(default=1_000_000, description="Maximum request body size in bytes")
    cors_origins: list[str] = Field(
        default_factory=list,
        description="Allowed CORS origins (JSON array or comma-separated)",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@cache
def get_settings() -> Settings:
    """
    Get cached application settings.
    """
    return Settings()
