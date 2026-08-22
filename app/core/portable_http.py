"""
Strict portable HTTP parsing and response negotiation.
"""

import json
import re
from collections.abc import Callable
from io import BytesIO
from typing import Any, override
from urllib.parse import unquote_to_bytes

import cbor2
from fastapi import Request, Response
from fastapi.routing import APIRoute
from fastapi.utils import is_body_allowed_for_status_code
from pydantic import BaseModel, ValidationError

from app.core.content_negotiation import (
    CBOR_MEDIA_TYPE,
    JSON_MEDIA_TYPE,
    negotiate_api_media_type,
    strip_http_ows,
)
from app.core.problems import PortableProblem, validation_issues

_BAD_PERCENT = re.compile(rb"%(?![0-9A-Fa-f]{2})")
_ASCII_DIGITS = re.compile(r"[0-9]+\Z")
_CURSOR = re.compile(r"[!-~]{1,2048}\Z")
_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_MIN_QUOTED_VALUE_LENGTH = 2
_MAX_LIMIT_DIGITS = 3
_MAX_PAGE_LIMIT = 100
_ASCII_CONTROL_LIMIT = 0x20
_ASCII_DELETE = 0x7F
_SURROGATE_MIN = 0xD800
_SURROGATE_MAX = 0xDFFF


class DuplicateJSONKeyError(ValueError):
    """Raised for duplicate JSON object member names."""


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKeyError
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(value)


def _contains_lone_surrogate(value: object) -> bool:
    if isinstance(value, str):
        return any(_SURROGATE_MIN <= ord(character) <= _SURROGATE_MAX for character in value)
    if isinstance(value, list):
        return any(_contains_lone_surrogate(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_lone_surrogate(key) or _contains_lone_surrogate(item) for key, item in value.items())
    return False


def parse_strict_json(data: bytes) -> object:
    if data.startswith(b"\xef\xbb\xbf"):
        raise PortableProblem("invalid_request")
    try:
        text = data.decode("utf-8", errors="strict")
        value = json.loads(text, object_pairs_hook=_reject_duplicate_pairs, parse_constant=_reject_constant)
        if _contains_lone_surrogate(value):
            raise ValueError
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateJSONKeyError, RecursionError, ValueError) as error:
        raise PortableProblem("invalid_request") from error
    return value


def parse_strict_cbor(data: bytes) -> object:
    try:
        stream = BytesIO(data)
        value = cbor2.CBORDecoder(stream, allow_duplicate_keys=False).decode()
        if stream.read(1):
            raise ValueError
    except (cbor2.CBORDecodeError, RecursionError, ValueError, TypeError) as error:
        raise PortableProblem("invalid_request") from error
    return value


def parse_query_string(raw_query: bytes) -> dict[str, str]:
    if not raw_query:
        return {}
    result: dict[str, str] = {}
    for raw_part in raw_query.split(b"&"):
        raw_name, separator, raw_value = raw_part.partition(b"=")
        if _BAD_PERCENT.search(raw_name) or _BAD_PERCENT.search(raw_value):
            raise PortableProblem("invalid_request")
        try:
            name = unquote_to_bytes(raw_name.replace(b"+", b" ")).decode("utf-8", errors="strict")
            value = unquote_to_bytes(raw_value.replace(b"+", b" ")).decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise PortableProblem("invalid_request") from error
        if not separator:
            value = ""
        if name in result:
            raise PortableProblem("invalid_request")
        result[name] = value
    return result


def validate_closed_query(raw_query: bytes, allowed: frozenset[str]) -> dict[str, str]:
    query = parse_query_string(raw_query)
    if any(name not in allowed for name in query):
        raise PortableProblem("invalid_request")
    cursor = query.get("cursor")
    if cursor is not None and _CURSOR.fullmatch(cursor) is None:
        raise PortableProblem("invalid_request")
    limit = query.get("limit")
    if limit is not None:
        normalized = limit.lstrip("0") or "0"
        if (
            _ASCII_DIGITS.fullmatch(limit) is None
            or len(normalized) > _MAX_LIMIT_DIGITS
            or not 1 <= int(normalized) <= _MAX_PAGE_LIMIT
        ):
            raise PortableProblem(
                "validation_failed",
                errors=[{"detail": "Request field is invalid", "source": {"parameter": "limit"}}],
            )
    return query


def request_query(request: Request) -> dict[str, str]:
    return request.scope.get("portable.query", {})


def _header_values(request: Request, name: bytes) -> list[str]:
    return [value.decode("latin1") for key, value in request.scope.get("headers", []) if key.lower() == name]


def _split_media_type(value: str) -> list[str] | None:
    parts: list[str] = []
    current: list[str] = []
    quoted = False
    escaped = False
    for character in value:
        if escaped:
            current.append(character)
            escaped = False
        elif quoted and character == "\\":
            current.append(character)
            escaped = True
        elif character == '"':
            current.append(character)
            quoted = not quoted
        elif character == ";" and not quoted:
            parts.append(strip_http_ows("".join(current)))
            current = []
        else:
            current.append(character)
    if quoted or escaped:
        return None
    parts.append(strip_http_ows("".join(current)))
    return None if any(not part for part in parts) else parts


def _decoded_parameter_value(value: str) -> str | None:
    if _TOKEN.fullmatch(value):
        return value
    if len(value) < _MIN_QUOTED_VALUE_LENGTH or not value.startswith('"') or not value.endswith('"'):
        return None
    result: list[str] = []
    escaped = False
    for character in value[1:-1]:
        if escaped:
            if character != "\t" and (ord(character) < _ASCII_CONTROL_LIMIT or ord(character) == _ASCII_DELETE):
                return None
            result.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character != "\t" and (
            ord(character) < _ASCII_CONTROL_LIMIT or character == '"' or ord(character) == _ASCII_DELETE
        ):
            return None
        else:
            result.append(character)
    return None if escaped else "".join(result)


def _request_content_type(value: str) -> str | None:
    parts = _split_media_type(value)
    if parts is None:
        return None
    base = parts[0].lower()
    if base == CBOR_MEDIA_TYPE:
        return CBOR_MEDIA_TYPE if len(parts) == 1 else None
    if base != JSON_MEDIA_TYPE or len(parts) > _MIN_QUOTED_VALUE_LENGTH:
        return None
    if len(parts) == 1:
        return JSON_MEDIA_TYPE
    name, equals, raw_value = parts[1].partition("=")
    decoded_value = _decoded_parameter_value(raw_value)
    if (
        not equals
        or name != strip_http_ows(name)
        or raw_value != strip_http_ows(raw_value)
        or name.lower() != "charset"
        or decoded_value is None
        or decoded_value.lower() != "utf-8"
    ):
        return None
    return JSON_MEDIA_TYPE


def _request_media_type(request: Request, body: bytes) -> str:
    content_types = _header_values(request, b"content-type")
    content_encodings = _header_values(request, b"content-encoding")
    if len(content_encodings) > 1 or (
        content_encodings
        and ("," in content_encodings[0] or strip_http_ows(content_encodings[0]).lower() != "identity")
    ):
        raise PortableProblem("unsupported_media_type")
    if len(content_types) != 1:
        if body or content_types:
            raise PortableProblem("unsupported_media_type")
        raise PortableProblem("invalid_request")
    content_type = _request_content_type(strip_http_ows(content_types[0]))
    if content_type is not None:
        return content_type
    raise PortableProblem("unsupported_media_type")


async def parse_request_model[T: BaseModel](request: Request, model: type[T]) -> T:
    body = await request.body()
    media_type = _request_media_type(request, body)
    if not body:
        raise PortableProblem("invalid_request")
    value = parse_strict_json(body) if media_type == JSON_MEDIA_TYPE else parse_strict_cbor(body)
    try:
        return model.model_validate(value, strict=True)
    except ValidationError as error:
        raise PortableProblem(
            "validation_failed",
            errors=validation_issues(error, location_prefix="body"),
        ) from error


def valid_json_content_type(value: str) -> bool:  # noqa: PLR0911
    parts = _split_media_type(value)
    if parts is None:
        return False
    if "/" not in parts[0]:
        return False
    media_type = parts[0].lower()
    type_name, subtype = media_type.split("/", maxsplit=1)
    if _TOKEN.fullmatch(type_name) is None or _TOKEN.fullmatch(subtype) is None:
        return False
    if media_type != JSON_MEDIA_TYPE and not (type_name == "application" and subtype.endswith("+json")):
        return False
    names: set[str] = set()
    for parameter in parts[1:]:
        raw_name, equals, parameter_value = parameter.partition("=")
        if not equals or raw_name != strip_http_ows(raw_name) or parameter_value != strip_http_ows(parameter_value):
            return False
        name = raw_name.lower()
        if _TOKEN.fullmatch(name) is None or name in names:
            return False
        if _decoded_parameter_value(parameter_value) is None:
            return False
        names.add(name)
    return True


class PortableRoute(APIRoute):
    """Negotiate every modeled GCP success before dependency resolution."""

    allow_cbor = True

    @override
    def get_route_handler(self) -> Callable[..., Any]:
        original_handler = super().get_route_handler()
        has_success_representation = self.status_code is None or is_body_allowed_for_status_code(self.status_code)

        async def custom_handler(request: Request) -> Response:
            success_media_type: str | None = None
            if has_success_representation:
                accept_values = request.headers.getlist("accept")
                success_media_type = negotiate_api_media_type(
                    ",".join(accept_values) if accept_values else None,
                    allow_cbor=self.allow_cbor,
                )
                if success_media_type is None:
                    raise PortableProblem("not_acceptable")
            response = await original_handler(request)
            if success_media_type == CBOR_MEDIA_TYPE and response.body:
                data = parse_strict_json(bytes(response.body))
                headers = {
                    key: value
                    for key, value in response.headers.items()
                    if key.lower() not in {"content-type", "content-length"}
                }
                return Response(
                    content=cbor2.dumps(data),
                    status_code=response.status_code,
                    headers=headers,
                    media_type=CBOR_MEDIA_TYPE,
                    background=response.background,
                )
            if success_media_type is not None and response.body:
                response.headers["Content-Type"] = success_media_type
            return response

        return custom_handler


class JSONOnlyRoute(PortableRoute):
    """Portable route whose success is JSON only."""

    allow_cbor = False
