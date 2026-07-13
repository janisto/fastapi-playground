"""
Health check router.
"""

from fastapi import APIRouter, Request, Response

from app.core.schema_links import build_described_by_link, build_schema_url
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
    schema_path = "/schemas/HealthResponse.json"
    response.headers["Link"] = build_described_by_link(schema_path)
    return HealthResponse(
        schema_url=build_schema_url(request, schema_path),
        status="healthy",
    )
