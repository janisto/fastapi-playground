"""Dependency-free portable liveness route."""

from fastapi import APIRouter, Response

from app.core.constants import API_CATALOG_LINK, OPENAPI_DOCUMENT_LINK
from app.core.portable_http import PortableRoute
from app.models.health import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"], route_class=PortableRoute)


@router.get(
    "",
    response_model=HealthResponse,
    summary="Get application health",
    description=(
        "Reports process liveness without checking Firebase, Firestore, or GitHub readiness. Public and "
        "side-effect free; Link headers locate the API catalog and OpenAPI document."
    ),
    operation_id="getHealth",
)
async def get_health(response: Response) -> HealthResponse:
    """Return the exact dependency-free liveness representation."""
    response.headers.append("Link", f"{API_CATALOG_LINK}, {OPENAPI_DOCUMENT_LINK}")
    return HealthResponse(status="healthy")
