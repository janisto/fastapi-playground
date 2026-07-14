"""
Configuration settings for the application.
"""

import json
from functools import cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def parse_cors_origins(value: object) -> list[str]:
    """
    Parse CORS origins from either JSON array or comma-separated string.

    Supports:
    - JSON array: '["http://localhost:3000", "https://example.com"]'
    - Comma-separated: 'http://localhost:3000,https://example.com'
    - Already-parsed list (passthrough)
    """
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            raise ValueError("CORS_ORIGINS entries must be strings")
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    if not isinstance(value, str):
        raise TypeError("CORS_ORIGINS must be a string or array of strings")

    if not value or not value.strip():
        return []

    value = value.strip()

    # Try JSON first (starts with '[')
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                if not all(isinstance(item, str) for item in parsed):
                    raise ValueError("CORS_ORIGINS entries must be strings")
                return [item.strip() for item in parsed if item.strip()]
        except json.JSONDecodeError as error:
            raise ValueError("CORS_ORIGINS must be a valid JSON array or comma-separated list") from error
        raise ValueError("CORS_ORIGINS JSON value must be an array")

    # Fall back to comma-separated
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """
    Application settings.
    """

    # Environment
    environment: Literal["development", "test", "production"] = Field(
        default="production", description="Environment name"
    )
    debug: bool = Field(default=False, description="Debug mode")

    # Firebase
    firebase_project_id: str = Field(..., min_length=1, description="Firebase project ID")
    google_application_credentials: str | None = Field(default=None, description="Path to service account credentials")
    firestore_database: str | None = Field(default=None, description="Firestore database ID (default: (default))")

    # Security / Limits
    max_request_size_bytes: int = Field(default=1_000_000, gt=0, description="Maximum request body size in bytes")

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
        default=["Authorization", "Content-Type", "traceparent", "tracestate", "X-Request-ID"],
        description="Allowed CORS headers",
    )
    cors_expose_headers: list[str] = Field(
        default=["Link", "Location", "X-Request-ID"],
        description="CORS headers exposed to browser",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins_field(cls, value: object) -> list[str]:
        """
        Parse CORS origins from JSON array or comma-separated string.
        """
        return parse_cors_origins(value)

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
