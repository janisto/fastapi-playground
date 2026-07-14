"""
Health check router.
"""

from fastapi import APIRouter, Request, Response

from app.core.cbor import NotAcceptableHTTPException
from app.core.content_negotiation import JSON_MEDIA_TYPE, negotiate_api_media_type
from app.core.openapi import problem_response, success_response
from app.core.schema_links import build_described_by_link
from app.models.health import HealthResponse

router = APIRouter(
    prefix="/health",
    tags=["Health"],
    responses={
        406: problem_response("Requested response format is not supported"),
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
async def health_check(request: Request, response: Response) -> HealthResponse:
    """
    Lightweight health probe for liveness checks.

    Returns a simple status response without database or external service checks.
    Suitable for Kubernetes liveness probes and load balancer health checks.
    """
    accept = ",".join(request.headers.getlist("accept"))
    if negotiate_api_media_type(accept, allow_cbor=False) is None:
        raise NotAcceptableHTTPException(JSON_MEDIA_TYPE)

    schema_path = "/schemas/HealthResponse.json"
    response.headers["Link"] = build_described_by_link(schema_path)
    return HealthResponse(status="healthy")
