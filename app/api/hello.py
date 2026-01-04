"""
Hello router demonstrating REST API guidelines.

This router provides example endpoints showing:
- GET with no parameters (200)
- POST with validation (201 Created, Location header)
- CBOR content negotiation via CBORRoute
- Validation errors (422 with structured format)
"""

from fastapi import APIRouter, Request, Response, status

from app.core.cbor import CBORRoute
from app.models.error import ProblemResponse, ValidationProblemResponse
from app.models.hello import GREETINGS, Greeting, GreetingRequest

router = APIRouter(
    prefix="/hello",
    tags=["Hello"],
    route_class=CBORRoute,
    responses={
        422: {"model": ValidationProblemResponse, "description": "Validation error"},
        500: {"model": ProblemResponse, "description": "Server error"},
    },
)


@router.get(
    "",
    summary="Get greeting",
    description="Returns a simple greeting message.",
    operation_id="hello_get",
    responses={
        200: {"model": Greeting, "description": "Greeting returned successfully"},
    },
)
async def get_greeting(request: Request, response: Response) -> Greeting:
    """
    Return a simple greeting message.

    Demonstrates a basic GET endpoint with no parameters that returns
    a JSON (or CBOR) response.
    """
    response.headers["Link"] = '</schemas/Greeting.json>; rel="describedBy"'
    return Greeting(
        schema_url=str(request.base_url) + "schemas/Greeting.json",
        message="Hello, World!",
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create personalized greeting",
    description="Creates a personalized greeting for the given name.",
    operation_id="hello_create",
    responses={
        201: {"model": Greeting, "description": "Greeting created successfully"},
        422: {"model": ValidationProblemResponse, "description": "Validation error"},
    },
)
async def create_greeting(http_request: Request, greeting_request: GreetingRequest, response: Response) -> Greeting:
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

    response.headers["Link"] = '</schemas/Greeting.json>; rel="describedBy"'
    return Greeting(
        schema_url=str(http_request.base_url) + "schemas/Greeting.json",
        message=message,
    )
