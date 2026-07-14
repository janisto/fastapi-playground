"""
CBOR serialization support (RFC 8949).

Provides bidirectional CBOR support with automatic content negotiation.
Content negotiation policy lives in app.core.content_negotiation.
"""

import json
from collections.abc import Callable
from datetime import UTC
from typing import Any

import cbor2
from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute
from fastapi.utils import is_body_allowed_for_status_code
from fastapi_problem.error import BadRequestProblem, StatusProblem
from starlette.requests import Request as StarletteRequest

from app.core.content_negotiation import (
    ALLOWED_CONTENT_TYPES,
    CBOR_MEDIA_TYPE,
    JSON_MEDIA_TYPE,
    content_type_is_allowed,
    content_type_matches,
    negotiate_api_media_type,
    negotiate_problem_media_type,
    normalize_media_type,
)


class CBORDecodeError(Exception):
    """
    Raised when CBOR decoding fails.
    """

    def __init__(self, detail: str = "Invalid CBOR data") -> None:
        self.detail = detail
        super().__init__(detail)


class CBORDecodeHTTPException(HTTPException):
    """
    HTTPException for CBOR decode errors.

    Used during body parsing where regular exceptions would be caught by FastAPI.
    The exception handler converts this to a proper Problem response.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=400, detail=detail)


class CBORDecodeProblem(BadRequestProblem):
    """
    Returned when CBOR decoding fails.
    """

    title = "Invalid CBOR"


class UnsupportedMediaTypeProblem(StatusProblem):
    """
    Returned when Content-Type is not supported.
    """

    title = "Unsupported Media Type"
    status = 415


class UnsupportedMediaTypeHTTPException(HTTPException):
    """
    HTTPException for unsupported Content-Type.

    Used during body parsing where regular Problems would be caught by FastAPI.
    The exception handler converts this to UnsupportedMediaTypeProblem.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=415, detail=detail)


class NotAcceptableProblem(StatusProblem):
    """
    Returned when none of the requested response formats are supported.
    """

    title = "Not Acceptable"
    status = 406


class NotAcceptableHTTPException(HTTPException):
    """
    HTTPException for unsupported Accept headers.
    """

    def __init__(self, *supported_media_types: str) -> None:
        supported = supported_media_types or (JSON_MEDIA_TYPE, CBOR_MEDIA_TYPE)
        super().__init__(status_code=406, detail=f"Supported response formats: {', '.join(supported)}")


class CBORRequest(StarletteRequest):
    """
    Request that decodes CBOR bodies to JSON for Pydantic validation.

    When Content-Type is application/cbor, the request body is decoded from CBOR
    and re-encoded as JSON so Pydantic can validate it normally. The Content-Type
    header is also updated so FastAPI correctly parses the body.
    """

    _cbor_decoded: bool = False

    async def body(self) -> bytes:
        """
        Get request body, decoding CBOR to JSON if necessary.

        Validates Content-Type against allowed types (case-insensitive per RFC 9110)
        and converts CBOR to JSON for downstream processing.
        """
        if not hasattr(self, "_body"):
            body = await super().body()
            content_type = self.headers.get("content-type", "")

            if body and content_type and not content_type_is_allowed(content_type, ALLOWED_CONTENT_TYPES):
                normalized = normalize_media_type(content_type)
                raise UnsupportedMediaTypeHTTPException(
                    detail=f"Content-Type '{normalized}' not supported. Use: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
                )

            if body and content_type_matches(content_type, CBOR_MEDIA_TYPE):
                try:
                    decoded = cbor2.loads(body)
                    body = json.dumps(decoded).encode("utf-8")
                    self._cbor_decoded = True
                    # Update Content-Type in scope headers so FastAPI parses as JSON
                    self._update_content_type_to_json()
                except cbor2.CBORDecodeError as e:
                    raise CBORDecodeHTTPException(f"Failed to decode CBOR: {e}") from e
                except (TypeError, ValueError) as e:
                    # Handle cases where CBOR decodes but cannot be serialized to JSON
                    # (e.g., break markers, undefined, or other non-JSON-serializable types)
                    raise CBORDecodeHTTPException(f"Failed to decode CBOR: {e}") from e

            self._body = body
        return self._body

    def _update_content_type_to_json(self) -> None:
        """
        Update Content-Type header in scope to application/json.
        """
        # Rebuild headers without original content-type, then add json content-type
        new_headers = [(key, value) for key, value in self.scope["headers"] if key.lower() != b"content-type"]
        new_headers.append((b"content-type", b"application/json"))
        self.scope["headers"] = new_headers
        # Clear cached _headers so next access rebuilds from scope
        if hasattr(self, "_headers"):
            del self._headers


class CBORRoute(APIRoute):
    """
    APIRoute with automatic CBOR content negotiation.

    Handles both request decoding (CBOR to JSON) and response encoding
    (JSON to CBOR) based on Content-Type and Accept headers respectively.

    Usage:
        router = APIRouter(route_class=CBORRoute)
    """

    def get_route_handler(self) -> Callable[..., Any]:
        """
        Return custom route handler with CBOR negotiation.

        Wraps the original handler to:
        1. Convert incoming CBOR requests to JSON for Pydantic validation
        2. Convert outgoing JSON responses to CBOR if Accept header requests it
        """
        original_handler = super().get_route_handler()
        has_success_representation = self.status_code is None or is_body_allowed_for_status_code(self.status_code)

        async def custom_handler(request: Request) -> Response:
            # RFC 9110 list-based fields can be split across multiple field lines.
            accept = ",".join(request.headers.getlist("accept"))

            success_media_type = negotiate_api_media_type(accept) if has_success_representation else None
            if has_success_representation and success_media_type is None:
                raise NotAcceptableHTTPException

            cbor_request = CBORRequest(request.scope, request.receive)

            # Pre-process body to trigger CBOR validation before route handler
            # This allows our custom exception handlers to process CBOR errors
            # CBORDecodeHTTPException and UnsupportedMediaTypeHTTPException propagate naturally
            await cbor_request.body()

            response = await original_handler(cbor_request)

            response_content_type = response.media_type or ""
            if success_media_type == CBOR_MEDIA_TYPE and content_type_matches(response_content_type, JSON_MEDIA_TYPE):
                body = response.body
                if body:
                    data = json.loads(bytes(body))
                    cbor_body = cbor2.dumps(data, datetime_as_timestamp=True, timezone=UTC)
                    # Exclude content-type and content-length from headers
                    # (will be set by Response based on media_type and content)
                    headers = {
                        k: v for k, v in response.headers.items() if k.lower() not in ("content-type", "content-length")
                    }
                    return Response(
                        content=cbor_body,
                        status_code=response.status_code,
                        headers=headers,
                        media_type=CBOR_MEDIA_TYPE,
                        background=response.background,
                    )
            return response

        return custom_handler


class CBORProblemPostHook:
    """
    Post-hook to serialize Problem Details as CBOR when client accepts it.

    Uses application/cbor only when the client explicitly prefers CBOR.

    RFC 9457 does not define application/problem+cbor. The registered RFC 9290
    concise CBOR format has a different data model and is not implemented here.
    Must be registered last in post_hooks.
    """

    def __call__(
        self,
        content: dict[str, Any],
        request: Request,
        response: Response,
    ) -> tuple[dict[str, Any], Response]:
        """
        Serialize error response as CBOR if client accepts it.

        Modifies response body and content-type header when Accept header
        explicitly prefers application/cbor.
        """
        accept = ",".join(request.headers.getlist("accept"))
        if negotiate_problem_media_type(accept) == CBOR_MEDIA_TYPE:
            cbor_body = cbor2.dumps(content)
            response.body = cbor_body
            response.headers["content-type"] = CBOR_MEDIA_TYPE
            response.headers["content-length"] = str(len(cbor_body))
        return content, response
