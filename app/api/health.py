"""Dependency-free portable liveness route."""

from fastapi import APIRouter

from app.core.portable_http import PortableRoute
from app.models.health import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"], route_class=PortableRoute)


@router.get(
    "",
    response_model=HealthResponse,
    summary="Get application health",
    description="Returns process liveness without invoking application dependencies.",
    operation_id="getHealth",
)
async def get_health() -> HealthResponse:
    """Return the exact dependency-free liveness representation."""
    return HealthResponse(status="healthy")
