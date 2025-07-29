"""
FastAPI application with Firebase Authentication and Firestore integration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.core.firebase import initialize_firebase
from app.core.logging import setup_logging
from app.routers import profile


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Initialize services
    setup_logging()
    initialize_firebase()

    yield


# Create FastAPI app with API documentation
app = FastAPI(
    title="FastAPI Playground",
    description="A FastAPI application with Firebase Authentication and Firestore",
    version="0.1.0",
    docs_url="/api-docs",
    redoc_url="/api-redoc",
    lifespan=lifespan,
)

# Include routers
app.include_router(profile.router, prefix="/profile", tags=["profile"])


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Hello World", "docs": "/api-docs"}


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
