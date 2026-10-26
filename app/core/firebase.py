"""
Firebase initialization and configuration.
"""

import logging
import os
from ipaddress import ip_address
from typing import cast
from urllib.parse import urlsplit

import firebase_admin
from firebase_admin import credentials, firestore_async
from google.auth.credentials import AnonymousCredentials
from google.cloud.firestore import AsyncClient

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Global Firebase app instance
_firebase_app: firebase_admin.App | None = None
_async_firestore_client: AsyncClient | None = None


def _is_loopback_endpoint(value: str | None) -> bool:
    """
    Validate a literal emulator host and port without resolving DNS.
    """
    if value is None or not value.isascii():
        return False
    try:
        parsed = urlsplit(f"//{value}")
        if (
            parsed.netloc != value
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.port is None
            or parsed.port == 0
            or parsed.hostname is None
        ):
            return False
        return parsed.hostname == "localhost" or ip_address(parsed.hostname).is_loopback
    except ValueError:
        return False


def _uses_local_emulators(settings: Settings) -> bool:
    """
    Permit credential-free SDK access only to a paired local demo environment.
    """
    hosts = (os.environ.get("FIREBASE_AUTH_EMULATOR_HOST"), os.environ.get("FIRESTORE_EMULATOR_HOST"))
    if all(host is None for host in hosts):
        return False
    if (
        settings.is_production
        or settings.firebase_project_id is None
        or not settings.firebase_project_id.startswith("demo-")
        or not all(_is_loopback_endpoint(host) for host in hosts)
    ):
        raise ValueError("Firebase emulators require paired loopback endpoints and a non-production demo project")
    return True


def initialize_firebase() -> None:
    """
    Initialize Firebase Admin SDK.

    Excluded from coverage: infrastructure initialization tested via E2E tests.
    """
    global _firebase_app

    if _firebase_app is not None:
        logger.info("Firebase already initialized")
        return

    settings = get_settings()

    try:
        if settings.firebase_project_id is None or not settings.firebase_project_id.strip():
            raise RuntimeError("Firebase project is not configured")
        if _uses_local_emulators(settings):
            _firebase_app = cast(
                "firebase_admin.App",
                firebase_admin.initialize_app(
                    AnonymousCredentials(), options={"projectId": settings.firebase_project_id}
                ),
            )
        elif bool(settings.google_application_credentials):
            # Use service account credentials
            cred = credentials.Certificate(settings.google_application_credentials)
            _firebase_app = cast(
                "firebase_admin.App", firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})
            )
        else:
            # Use default credentials (for Cloud Run) with an explicit Firebase project.
            _firebase_app = cast(
                "firebase_admin.App", firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
            )

        logger.info("Firebase initialized successfully")

    except Exception as error:
        logger.error(  # noqa: TRY400 - provider details and credential paths must not enter logs
            "Firebase initialization failed",
            extra={"failure_type": type(error).__name__},
        )
        raise


def get_firebase_app() -> firebase_admin.App:
    """
    Get the Firebase app instance.
    """
    if _firebase_app is None:
        initialize_firebase()
    if _firebase_app is None:  # pragma: no cover - initialization either returns an app or raises
        raise RuntimeError("Firebase initialization did not produce an app")
    return _firebase_app


def get_async_firestore_client() -> AsyncClient:
    """
    Get or create the async Firestore client (lazy singleton).

    Supports optional database configuration for projects using multiple Firestore databases.
    """
    global _async_firestore_client
    if _async_firestore_client is None:
        settings = get_settings()
        _async_firestore_client = firestore_async.client(
            app=get_firebase_app(),
            database_id=settings.firestore_database,
        )
    return _async_firestore_client


def close_async_firestore_client() -> None:
    """
    Close the async Firestore client (call on shutdown).
    """
    global _async_firestore_client
    if _async_firestore_client is not None:
        _async_firestore_client.close()
        _async_firestore_client = None
