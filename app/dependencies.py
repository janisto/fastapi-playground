"""Application dependencies."""

from app.auth.firebase import FirebaseUser, verify_firebase_token
from app.services.profile import ProfileService, profile_service

# Dependency functions for FastAPI
get_current_user = verify_firebase_token

__all__ = [
    "FirebaseUser",
    "get_current_user",
    "ProfileService",
    "profile_service",
]
