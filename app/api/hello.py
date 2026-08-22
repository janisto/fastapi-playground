"""Portable dependency-free greeting routes."""

from fastapi import APIRouter, Request, status

from app.core.constants import API_V1_PREFIX
from app.core.portable_http import PortableRoute, parse_request_model
from app.models.hello import Greeting, HelloCreate

router = APIRouter(prefix=f"{API_V1_PREFIX}/hello", tags=["Hello"], route_class=PortableRoute)


@router.get(
    "",
    response_model=Greeting,
    summary="Get the default greeting",
    description="Returns the exact world greeting without dependencies.",
    operation_id="getHello",
)
async def get_hello() -> Greeting:
    """Return the portable world greeting."""
    return Greeting(message="Hello, World!")


@router.post(
    "",
    response_model=Greeting,
    status_code=status.HTTP_200_OK,
    summary="Create a personalized greeting",
    description="Validates a name and returns it verbatim in a greeting.",
    operation_id="createHello",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": {"$ref": "#/components/schemas/HelloCreate"}},
                "application/cbor": {"schema": {"$ref": "#/components/schemas/HelloCreate"}},
            },
        }
    },
)
async def create_hello(request: Request) -> Greeting:
    """Strictly parse and compute a personalized greeting."""
    greeting = await parse_request_model(request, HelloCreate)
    return Greeting(message=f"Hello, {greeting.name}!")
