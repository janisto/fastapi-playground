"""
API routers with versioning.
"""

from app.api import github, health, hello, items, profile, schemas

business_routers = (profile.router, hello.router, items.router, github.router)

__all__ = ["business_routers", "health", "schemas"]
