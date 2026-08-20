"""Runtime OpenAPI discovery route."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.portable_http import JSONOnlyRoute

router = APIRouter(tags=["Documentation"], route_class=JSONOnlyRoute)


@router.get("/openapi.json", include_in_schema=False, operation_id="getOpenApiDocument")
async def get_openapi_document(request: Request) -> JSONResponse:
    """Serve the document generated from this exact running application."""
    return JSONResponse(content=request.app.openapi())
