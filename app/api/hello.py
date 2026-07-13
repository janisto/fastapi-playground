"""
Hello router demonstrating REST API guidelines.

This router provides example endpoints showing:
- GET with no parameters (200)
- POST with validation (201 Created, Location header)
- CBOR content negotiation via CBORRoute
- Validation errors (422 with structured format)
"""

from fastapi import APIRouter, Response, status

from app.core.cbor import CBORRoute
from app.core.constants import API_V1_PREFIX
from app.core.openapi import COMMON_CBOR_RESPONSES, problem_response, success_response
from app.core.schema_links import build_described_by_link
from app.models.error import ValidationProblemResponse
from app.models.hello import GREETINGS, Greeting, GreetingRequest

router = APIRouter(
    prefix=f"{API_V1_PREFIX}/hello",
    tags=["Hello"],
    route_class=CBORRoute,
    responses=COMMON_CBOR_RESPONSES,
)

GREETING_SCHEMA_PATH = "/schemas/Greeting.json"


@router.get(
    "",
    summary="Get greeting",
    description="Returns a simple greeting message.",
    operation_id="hello_get",
    responses={
        200: success_response("Greeting returned successfully", "Greeting"),
    },
)
async def get_greeting(response: Response) -> Greeting:
    """
    Return a simple greeting message.

    Demonstrates a basic GET endpoint with no parameters that returns
    a JSON (or CBOR) response.
    """
    response.headers["Link"] = build_described_by_link(GREETING_SCHEMA_PATH)
    return Greeting(message="Hello, World!")


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create personalized greeting",
    description="Creates a personalized greeting for the given name.",
    operation_id="hello_create",
    responses={
        201: success_response("Greeting created successfully", "Greeting"),
        422: problem_response("Validation error", model=ValidationProblemResponse),
    },
)
async def create_greeting(greeting_request: GreetingRequest, response: Response) -> Greeting:
    """
    Create a personalized greeting.

    Demonstrates POST endpoint with:
    - Request body validation
    - 201 Created status code
    - Validation errors (422) for invalid input

    Note: No Location header since this creates a transient greeting,
    not a persistent resource retrievable at a URI.
    """
    greeting_word = GREETINGS[greeting_request.language]
    message = f"{greeting_word}, {greeting_request.name}!"

    response.headers["Link"] = build_described_by_link(GREETING_SCHEMA_PATH)
    return Greeting(message=message)
