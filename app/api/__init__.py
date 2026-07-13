"""
API routers with versioning.
"""

from app.api import health, hello, items, profile, schemas

business_routers = (profile.router, hello.router, items.router)

__all__ = ["business_routers", "health", "schemas"]
