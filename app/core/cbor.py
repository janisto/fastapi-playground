"""
CBOR serialization support (RFC 8949).

Provides bidirectional CBOR support with automatic content negotiation.
Content negotiation follows RFC 9110 (HTTP Semantics):
- Media types are case-insensitive (Section 8.3.1)
- Content codings are case-insensitive (Section 8.4.1)
- Accept header parsing handles quality values (Section 12.5.1)
"""

import json
from collections.abc import Callable
from datetime import UTC
from typing import Any

import cbor2
from fastapi import HTTPException, Request, Response
from fastapi.routing import APIRoute
from fastapi_problem.error import BadRequestProblem, StatusProblem
from starlette.requests import Request as StarletteRequest

CBOR_MEDIA_TYPE = "application/cbor"
JSON_MEDIA_TYPE = "application/json"
PROBLEM_CBOR = "application/problem+cbor"
PROBLEM_JSON = "application/problem+json"
# Lowercase set for case-insensitive comparison
ALLOWED_CONTENT_TYPES = frozenset({JSON_MEDIA_TYPE, CBOR_MEDIA_TYPE})


def normalize_media_type(media_type: str) -> str:
    """
    Normalize a media type for comparison per RFC 9110 Section 8.3.1.

    Media types are case-insensitive. This extracts the type/subtype portion,
    strips parameters (like charset), and converts to lowercase.
    """
    # Split off parameters (e.g., "application/json; charset=utf-8" -> "application/json")
    base_type = media_type.split(";", maxsplit=1)[0].strip()
    return base_type.lower()


def _parse_qvalue(params: list[str]) -> float | None:
    """
    Parse a quality value from media type parameters.
    """
    for raw_param in params:
        param = raw_param.strip()
        if param.lower().startswith("q="):
            try:
                quality = float(param[2:])
            except ValueError:
                return None
            return quality if 0 <= quality <= 1 else None
    return 1.0


def _media_range_specificity(range_type: str, target: str, target_parts: list[str]) -> int | None:
    """
    Return the matching media range specificity.
    """
    if range_type == target:
        return 2
    if range_type == "*/*":
        return 0
    range_parts = range_type.split("/")
    if len(range_parts) == 2 and range_parts[1] == "*" and range_parts[0] == target_parts[0]:
        return 1
    return None


def accepts_media_type(accept_header: str, media_type: str, *, explicit_only: bool = False) -> bool:
    """
    Check if Accept header includes specified media type per RFC 9110 Section 12.5.1.

    Handles:
    - Case-insensitive comparison
    - Quality values (q=0 means not acceptable)
    - Multiple media types separated by commas
    - Wildcard matching (*/* and type/*) unless explicit_only=True

    Args:
        accept_header: The Accept header value
        media_type: The media type to check for
        explicit_only: If True, wildcards (*/* and type/*) are not matched.
            Use this when checking for non-default content types like CBOR
            that should only be returned when explicitly requested.

    More specific media ranges take precedence over wildcards, including an
    explicit q=0 exclusion.
    """
    if not accept_header:
        return False

    return _media_type_quality(accept_header, media_type, explicit_only=explicit_only) > 0


def _media_type_quality(accept_header: str, media_type: str, *, explicit_only: bool = False) -> float:
    """
    Return the effective quality for a supported media type.
    """
    if not accept_header:
        return 0.0

    target = normalize_media_type(media_type)
    target_parts = target.split("/")

    best_specificity = -1
    best_quality = 0.0

    for raw_item in accept_header.split(","):
        item = raw_item.strip()
        if not item:
            continue

        # Split media type from parameters
        parts = item.split(";")
        range_type = normalize_media_type(parts[0])

        quality = _parse_qvalue(parts[1:])
        if quality is None:
            continue

        # Skip malformed media ranges
        if "/" not in range_type:
            continue

        specificity = _media_range_specificity(range_type, target, target_parts)
        if specificity is None or (explicit_only and specificity < 2):
            continue
        if specificity > best_specificity:
            best_specificity = specificity
            best_quality = quality
        elif specificity == best_specificity:
            best_quality = max(best_quality, quality)

    return best_quality


def negotiate_response_media_type(
    accept_header: str,
    *,
    problem: bool = False,
    allow_cbor: bool = True,
) -> str | None:
    """
    Select the preferred supported response media type.

    JSON is the server preference for absent headers, wildcards, and equal
    client quality. CBOR must be requested explicitly.
    """
    if not accept_header:
        return PROBLEM_JSON if problem else JSON_MEDIA_TYPE

    json_types = (PROBLEM_JSON, JSON_MEDIA_TYPE) if problem else (JSON_MEDIA_TYPE,)
    cbor_types = (PROBLEM_CBOR, CBOR_MEDIA_TYPE) if problem else (CBOR_MEDIA_TYPE,)
    json_quality = max(_media_type_quality(accept_header, media_type) for media_type in json_types)
    cbor_quality = (
        max(_media_type_quality(accept_header, media_type, explicit_only=True) for media_type in cbor_types)
        if allow_cbor
        else 0.0
    )

    if json_quality <= 0 and cbor_quality <= 0:
        return None
    if cbor_quality > json_quality:
        return PROBLEM_CBOR if problem else CBOR_MEDIA_TYPE
    return PROBLEM_JSON if problem else JSON_MEDIA_TYPE


def content_type_matches(content_type: str, media_type: str) -> bool:
    """
    Check if Content-Type matches specified media type per RFC 9110 Section 8.3.1.

    Media types are case-insensitive.
    """
    return normalize_media_type(content_type) == normalize_media_type(media_type)


def content_type_is_allowed(content_type: str, allowed: frozenset[str]) -> bool:
    """
    Check if Content-Type is in allowed set (case-insensitive).
    """
    normalized = normalize_media_type(content_type)
    return normalized in allowed


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

        async def custom_handler(request: Request) -> Response:
            # Capture Accept header from scope directly before body processing
            # (body processing may modify scope headers for CBOR->JSON conversion)
            accept = ""
            for key, value in request.scope.get("headers", []):
                if key == b"accept":
                    accept = value.decode("latin1")
                    break

            success_media_type = negotiate_response_media_type(accept)
            if success_media_type is None:
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

    Accepts both application/cbor and application/problem+cbor per RFC 9457
    content negotiation patterns. Must be registered last in post_hooks.
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
        includes application/cbor or application/problem+cbor
        (per RFC 9110 content negotiation).
        """
        accept = request.headers.get("accept", "")
        if negotiate_response_media_type(accept, problem=True) == PROBLEM_CBOR:
            cbor_body = cbor2.dumps(content)
            response.body = cbor_body
            response.headers["content-type"] = PROBLEM_CBOR
            response.headers["content-length"] = str(len(cbor_body))
        return content, response
