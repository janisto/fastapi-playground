"""
Health check router.
"""

from fastapi import APIRouter, Request, Response

from app.models.error import ProblemResponse
from app.models.health import HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["Health"],
    responses={
        500: {"model": ProblemResponse, "description": "Server error"},
    },
)


@router.get(
    "",
    response_model=HealthResponse,
    summary="Service health",
    description="Lightweight health probe for liveness checks.",
    operation_id="health_get",
    responses={
        200: {"model": HealthResponse, "description": "Service is healthy"},
    },
)
async def health_check(request: Request, response: Response) -> HealthResponse:
    """
    Lightweight health probe for liveness checks.

    Returns a simple status response without database or external service checks.
    Suitable for Kubernetes liveness probes and load balancer health checks.
    """
    response.headers["Link"] = '</schemas/HealthResponse.json>; rel="describedBy"'
    return HealthResponse(
        schema_url=str(request.base_url) + "schemas/HealthResponse.json",
        message="healthy",
    )
