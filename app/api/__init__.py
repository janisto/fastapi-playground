"""API routers with versioning."""

from fastapi import APIRouter

from app.api import health, hello, items, profile, schemas

# Versioned router for business endpoints
v1_router = APIRouter(prefix="/v1")
v1_router.include_router(profile.router)
v1_router.include_router(hello.router)
v1_router.include_router(items.router)

__all__ = ["health", "hello", "items", "profile", "schemas", "v1_router"]
