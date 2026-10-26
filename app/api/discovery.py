"""
Public same-build API catalog and curated usage guides.
"""

from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from app.core.constants import API_CATALOG_LINK, LLMS_INDEX_LINK
from app.core.content_negotiation import negotiate_media_type
from app.core.problems import PortableProblem

router = APIRouter(tags=["Documentation"])

_CATALOG_MEDIA_TYPE = 'application/linkset+json; profile="https://www.rfc-editor.org/info/rfc9727"'
_GUIDE_MEDIA_TYPE = "text/plain; charset=utf-8"
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_GUIDES = {f"/{name}": (_REPOSITORY_ROOT / name).read_bytes() for name in ("llms.txt", "llms-full.txt")}


def _require_representation(request: Request, media_type: str) -> None:
    """
    Reuse RFC 9110 matching without offering API JSON or CBOR aliases.
    """
    values = request.headers.getlist("accept")
    accept = ",".join(values) if values else None
    if negotiate_media_type(accept, (media_type,), default=media_type) is None:
        raise PortableProblem("not_acceptable")


@router.api_route("/.well-known/api-catalog", methods=["GET", "HEAD"], include_in_schema=False)
async def get_api_catalog(request: Request) -> Response:
    """
    Link to this application's local descriptions without probing their targets.
    """
    _require_representation(request, _CATALOG_MEDIA_TYPE)
    response = JSONResponse(
        {
            "linkset": [
                {
                    "anchor": "/",
                    "service-desc": [{"href": "/openapi.json", "type": "application/json"}],
                    "service-doc": [
                        {"href": "/llms.txt", "type": "text/plain"},
                        {"href": "/llms-full.txt", "type": "text/plain"},
                    ],
                    "status": [{"href": "/health", "type": "application/json"}],
                }
            ]
        },
        media_type=_CATALOG_MEDIA_TYPE,
        headers={"Link": f"{API_CATALOG_LINK}, {LLMS_INDEX_LINK}"},
    )
    if request.method == "HEAD":
        response.body = b""
    return response


@router.get("/llms.txt", include_in_schema=False)
@router.get("/llms-full.txt", include_in_schema=False)
async def get_usage_guide(request: Request) -> Response:
    """
    Serve only the two curated files bundled with this application build.
    """
    _require_representation(request, _GUIDE_MEDIA_TYPE)
    headers = {"Link": LLMS_INDEX_LINK} if request.url.path == "/llms-full.txt" else None
    return Response(content=_GUIDES[request.url.path], media_type=_GUIDE_MEDIA_TYPE, headers=headers)
