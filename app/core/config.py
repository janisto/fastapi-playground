"""
Configuration settings for the application.
"""

import json
from functools import cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def parse_cors_origins(value: str | list[str]) -> list[str]:
    """
    Parse CORS origins from either JSON array or comma-separated string.

    Supports:
    - JSON array: '["http://localhost:3000", "https://example.com"]'
    - Comma-separated: 'http://localhost:3000,https://example.com'
    - Already-parsed list (passthrough)
    """
    if isinstance(value, list):
        return value

    if not value or not value.strip():
        return []

    value = value.strip()

    # Try JSON first (starts with '[')
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if item]
        except json.JSONDecodeError:
            pass

    # Fall back to comma-separated
    return [item.strip() for item in value.split(",") if item.strip()]


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

    # CORS configuration - when allow_credentials=True, wildcards are forbidden per CORS spec
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=list,
        description="Allowed CORS origins (JSON array or comma-separated)",
    )
    cors_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        description="Allowed CORS methods",
    )
    cors_headers: list[str] = Field(
        default=["Authorization", "Content-Type", "traceparent", "X-Request-ID"],
        description="Allowed CORS headers",
    )
    cors_expose_headers: list[str] = Field(
        default=["Link", "Location", "X-Request-ID"],
        description="CORS headers exposed to browser",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins_field(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from JSON array or comma-separated string."""
        return parse_cors_origins(v)

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
