"""
Firebase initialization and configuration.
"""

import logging

import firebase_admin
from firebase_admin import credentials
from google.cloud.firestore import AsyncClient, Client

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global Firebase app instance
_firebase_app: firebase_admin.App | None = None
_firestore_client: Client | None = None
_async_firestore_client: AsyncClient | None = None


def initialize_firebase() -> None:  # pragma: no cover
    """
    Initialize Firebase Admin SDK.

    Excluded from coverage: infrastructure initialization tested via E2E tests.
    """
    global _firebase_app, _firestore_client

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
            # Use default credentials (for Cloud Run)
            _firebase_app = firebase_admin.initialize_app()

        # Initialize Firestore client (required)
        # Import inside function to avoid import-time failure on module import in environments where
        # Firestore is not needed during testing; failures will surface when initialization runs.
        from firebase_admin import firestore as _fb_firestore

        _firestore_client = _fb_firestore.client()
        logger.info("Firebase initialized successfully (with Firestore)")

    except Exception:
        logger.exception("Failed to initialize Firebase")
        raise


def get_firestore_client() -> Client:
    """
    Get the Firestore client instance.
    """
    if _firestore_client is None:
        raise RuntimeError(
            "Firestore client is not available. Ensure Firebase is initialized and google-cloud-firestore is installed."
        )
    return _firestore_client


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


async def close_async_firestore_client() -> None:
    """
    Close the async Firestore client (call on shutdown).
    """
    global _async_firestore_client
    if _async_firestore_client is not None:
        await _async_firestore_client.close()
        _async_firestore_client = None
