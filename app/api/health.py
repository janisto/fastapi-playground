"""
Health check router.
"""

from fastapi import APIRouter, Response

from app.core.openapi import problem_response, success_response
from app.core.schema_links import build_described_by_link
from app.models.health import HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["Health"],
    responses={
        413: problem_response("Request body is too large"),
        500: problem_response("Server error"),
    },
)


@router.get(
    "",
    response_model=HealthResponse,
    summary="Service health",
    description="Lightweight health probe for liveness checks.",
    operation_id="health_get",
    responses={
        200: success_response("Service is healthy", "HealthResponse", cbor=False),
    },
)
async def health_check(response: Response) -> HealthResponse:
    """
    Lightweight health probe for liveness checks.

    Returns a simple status response without database or external service checks.
    Suitable for Kubernetes liveness probes and load balancer health checks.
    """
    schema_path = "/schemas/HealthResponse.json"
    response.headers["Link"] = build_described_by_link(schema_path)
    return HealthResponse(status="healthy")
