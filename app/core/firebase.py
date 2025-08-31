"""Firebase initialization and configuration."""

import logging

import firebase_admin
from firebase_admin import credentials

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global Firebase app instance
_firebase_app: firebase_admin.App | None = None
_firestore_client: object | None = None


def initialize_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    global _firebase_app, _firestore_client

    if _firebase_app is not None:
        logger.info("Firebase already initialized")
        return

    settings = get_settings()

    try:
        if settings.firebase_credentials_path:
            # Use service account credentials
            cred = credentials.Certificate(settings.firebase_credentials_path)
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

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise


def get_firestore_client() -> object:
    """Get the Firestore client instance."""
    if _firestore_client is None:
        raise RuntimeError(
            "Firestore client is not available. Ensure Firebase is initialized and google-cloud-firestore is installed."
        )
    return _firestore_client


def get_firebase_app() -> firebase_admin.App:
    """Get the Firebase app instance."""
    if _firebase_app is None:
        raise RuntimeError("Firebase not initialized. Call initialize_firebase() first.")
    return _firebase_app
