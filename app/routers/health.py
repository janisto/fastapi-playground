"""
Health check router.
"""

from fastapi import APIRouter

from app.models.health import HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Service health",
    description="Lightweight health probe for liveness checks.",
    operation_id="health_get",
    responses={
        200: {"model": HealthResponse, "description": "Service is healthy"},
    },
)
async def health_check() -> HealthResponse:
    """
    Lightweight health probe for liveness checks.

    Returns a simple status response without database or external service checks.
    Suitable for Kubernetes liveness probes and load balancer health checks.
    """
    return HealthResponse(status="healthy")
