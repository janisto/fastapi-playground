"""
Application dependencies.
"""

from typing import Annotated

from fastapi import Depends

from app.auth.firebase import FirebaseUser, verify_firebase_token
from app.services.github_service import GitHubService
from app.services.profile import ProfileService

# Auth dependency type alias
CurrentUser = Annotated[FirebaseUser, Depends(verify_firebase_token)]


def get_profile_service() -> ProfileService:
    """
    Dependency provider for ProfileService.
    """
    return ProfileService()


# Service dependency type alias
ProfileServiceDependency = Annotated[ProfileService, Depends(get_profile_service)]


def get_github_service() -> GitHubService:
    """Provide the credential-free GitHub service."""
    return GitHubService()


GitHubServiceDependency = Annotated[GitHubService, Depends(get_github_service)]

__all__ = [
    "CurrentUser",
    "FirebaseUser",
    "GitHubService",
    "GitHubServiceDependency",
    "ProfileService",
    "ProfileServiceDependency",
    "get_github_service",
    "get_profile_service",
]
