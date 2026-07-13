"""
Firebase initialization and configuration.
"""

import logging

import firebase_admin
from firebase_admin import credentials
from google.cloud.firestore import AsyncClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global Firebase app instance
_firebase_app: firebase_admin.App | None = None
_async_firestore_client: AsyncClient | None = None


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
        if settings.google_application_credentials:
            # Use service account credentials
            cred = credentials.Certificate(settings.google_application_credentials)
            _firebase_app = firebase_admin.initialize_app(cred, {"projectId": settings.firebase_project_id})
        else:
            # Use default credentials (for Cloud Run) with an explicit Firebase project.
            _firebase_app = firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})

        logger.info("Firebase initialized successfully")

    except Exception:
        logger.exception("Failed to initialize Firebase")
        raise


def get_firebase_app() -> firebase_admin.App:
    """
    Get the Firebase app instance.
    """
    if _firebase_app is None:
        raise RuntimeError("Firebase not initialized. Call initialize_firebase() first.")
    return _firebase_app


def get_async_firestore_client() -> AsyncClient:
    """
    Get or create the async Firestore client (lazy singleton).

    Supports optional database configuration for projects using multiple Firestore databases.
    """
    global _async_firestore_client
    if _async_firestore_client is None:
        settings = get_settings()
        _async_firestore_client = AsyncClient(
            project=settings.firebase_project_id,
            database=settings.firestore_database,
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
