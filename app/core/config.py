"""Configuration settings for the application."""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8080, alias="PORT")

    # Firebase
    firebase_project_id: str = Field(default="test-project", alias="FIREBASE_PROJECT_ID")
    firebase_credentials_path: Optional[str] = Field(default=None, alias="GOOGLE_APPLICATION_CREDENTIALS")

    # Google Cloud
    gcp_project_id: str = Field(default="test-project", alias="GCP_PROJECT_ID")

    # Secrets
    secret_manager_enabled: bool = Field(default=True, alias="SECRET_MANAGER_ENABLED")

    # Database
    firestore_collection_profiles: str = Field(default="profiles", alias="FIRESTORE_COLLECTION_PROFILES")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
