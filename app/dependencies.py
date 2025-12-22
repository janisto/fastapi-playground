"""
Application dependencies.
"""

from typing import Annotated

from fastapi import Depends

from app.auth.firebase import FirebaseUser, verify_firebase_token
from app.services.profile import ProfileService

# Auth dependency type alias
CurrentUser = Annotated[FirebaseUser, Depends(verify_firebase_token)]


def get_profile_service() -> ProfileService:
    """
    Dependency provider for ProfileService.
    """
    return ProfileService()


# Service dependency type alias
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]

__all__ = [
    "CurrentUser",
    "FirebaseUser",
    "ProfileService",
    "ProfileServiceDep",
    "get_profile_service",
]
