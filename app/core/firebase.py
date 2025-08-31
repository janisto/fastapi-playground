"""Firebase initialization and configuration."""

import logging

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as firestore_client

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global Firebase app instance
_firebase_app: firebase_admin.App | None = None
_firestore_client: firestore_client.Client | None = None


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

        # Initialize Firestore client
        _firestore_client = firestore.client()

        logger.info("Firebase initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        raise


def get_firestore_client() -> firestore_client.Client:
    """Get the Firestore client instance."""
    if _firestore_client is None:
        raise RuntimeError("Firebase not initialized. Call initialize_firebase() first.")
    return _firestore_client


def get_firebase_app() -> firebase_admin.App:
    """Get the Firebase app instance."""
    if _firebase_app is None:
        raise RuntimeError("Firebase not initialized. Call initialize_firebase() first.")
    return _firebase_app
