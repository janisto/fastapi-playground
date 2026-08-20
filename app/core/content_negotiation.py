"""
HTTP media-type negotiation for API responses and request bodies.

Success negotiation honors RFC 9110 Accept ranges strictly. Error negotiation
is best effort: it preserves the original error status and falls back to RFC
9457 JSON Problem Details when the requested representation is unavailable.
"""

import re

CBOR_MEDIA_TYPE = "application/cbor"
JSON_MEDIA_TYPE = "application/json"
PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"
SCHEMA_JSON_MEDIA_TYPE = "application/schema+json"

ALLOWED_CONTENT_TYPES = frozenset({JSON_MEDIA_TYPE, CBOR_MEDIA_TYPE})

_QVALUE_PATTERN = re.compile(r"(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)\Z")
_TOKEN_PATTERN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_EXACT_MEDIA_RANGE_SPECIFICITY = 2
_MEDIA_TYPE_PARTS = 2
_MIN_QUOTED_VALUE_LENGTH = 2
_ASCII_CONTROL_BOUNDARY = 0x20
_ASCII_DELETE = 0x7F


def _split_quoted(value: str, separator: str) -> list[str] | None:
    """
    Split an HTTP field value without treating quoted separators as delimiters.

    Return None when the quoted-string syntax is incomplete.
    """
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
        elif character == separator and not quoted:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)

    if quoted or escaped:
        return None

    parts.append("".join(current))
    return parts


def normalize_media_type(media_type: str) -> str:
    """
    Normalize a media type for case-insensitive comparison.
    """
    return media_type.split(";", maxsplit=1)[0].strip().lower()


def _parameter_value(value: str) -> str | None:
    value = value.strip()
    if _TOKEN_PATTERN.fullmatch(value):
        return value
    if len(value) < _MIN_QUOTED_VALUE_LENGTH or not value.startswith('"') or not value.endswith('"'):
        return None
    result: list[str] = []
    escaped = False
    for character in value[1:-1]:
        if escaped:
            result.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif ord(character) < _ASCII_CONTROL_BOUNDARY or ord(character) == _ASCII_DELETE:
            return None
        else:
            result.append(character)
    return None if escaped else "".join(result)


def _parse_parameters(params: list[str]) -> tuple[float, dict[str, str]] | None:
    """
    Parse one range's quality and media parameters.
    """
    quality = 1.0
    qvalue_seen = False
    media_parameters: dict[str, str] = {}
    for raw_param in params:
        param = raw_param.strip()
        if not param:
            return None
        raw_name, separator, raw_value = param.partition("=")
        name = raw_name.lower()
        if (
            not separator
            or raw_name != raw_name.strip()
            or raw_value != raw_value.strip()
            or _TOKEN_PATTERN.fullmatch(name) is None
        ):
            return None
        if name == "q":
            value = raw_value
            if qvalue_seen or _QVALUE_PATTERN.fullmatch(value) is None:
                return None
            quality = float(value)
            qvalue_seen = True
        else:
            value = _parameter_value(raw_value)
            if value is None:
                return None
            if name in media_parameters:
                return None
            media_parameters[name] = value.lower() if name == "charset" else value
    return quality, media_parameters


def _parse_media_value(value: str) -> tuple[str, dict[str, str]] | None:
    parts = _split_quoted(value, ";")
    if parts is None or not parts:
        return None
    base = parts[0].strip().lower()
    type_parts = base.split("/")
    if (
        len(type_parts) != _MEDIA_TYPE_PARTS
        or not all(part == "*" or _TOKEN_PATTERN.fullmatch(part) for part in type_parts)
        or (type_parts[0] == "*" and type_parts[1] != "*")
    ):
        return None
    parsed = _parse_parameters(parts[1:])
    if parsed is None:
        return None
    _, parameters = parsed
    if "q" in parameters:
        return None
    return base, parameters


def _media_range_specificity(range_type: str, target: str, target_parts: list[str]) -> int | None:
    """
    Return the RFC 9110 specificity of a matching media range.
    """
    if range_type == target:
        return _EXACT_MEDIA_RANGE_SPECIFICITY
    if range_type == "*/*":
        return 0
    range_parts = range_type.split("/")
    if len(range_parts) == _MEDIA_TYPE_PARTS and range_parts[1] == "*" and range_parts[0] == target_parts[0]:
        return 1
    return None


def _media_type_quality(  # noqa: C901 - RFC media-range precedence is clearer as one selection pass
    accept_header: str | None,
    media_type: str,
    *,
    explicit_only: bool = False,
) -> float | None:
    """
    Return the effective quality of a media type, or None when it is not listed.

    The most specific matching range wins, so an exact q=0 exclusion overrides
    broader wildcards. When explicit_only is true, wildcards do not match.
    """
    if accept_header is None:
        return None

    parsed_target = _parse_media_value(media_type)
    if parsed_target is None:
        raise ValueError("candidate media type is malformed")
    target, target_parameters = parsed_target
    target_parts = target.split("/")
    best_specificity = (-1, -1)
    best_quality = 0.0

    raw_items = _split_quoted(accept_header, ",")
    if raw_items is None:
        return None

    for raw_item in raw_items:
        item = raw_item.strip()
        if not item:
            continue

        parts = _split_quoted(item, ";")
        if parts is None or not parts:
            continue
        range_type = parts[0].strip().lower()
        range_parts = range_type.split("/")
        if (
            len(range_parts) != _MEDIA_TYPE_PARTS
            or not all(part == "*" or _TOKEN_PATTERN.fullmatch(part) for part in range_parts)
            or (range_parts[0] == "*" and range_parts[1] != "*")
        ):
            continue
        parsed_parameters = _parse_parameters(parts[1:])
        if parsed_parameters is None:
            continue
        quality, media_parameters = parsed_parameters

        specificity = _media_range_specificity(range_type, target, target_parts)
        if specificity is None or (explicit_only and specificity < _EXACT_MEDIA_RANGE_SPECIFICITY):
            continue
        if any(target_parameters.get(name) != value for name, value in media_parameters.items()):
            continue
        candidate_specificity = (specificity, len(media_parameters))
        if candidate_specificity > best_specificity:
            best_specificity = candidate_specificity
            best_quality = quality
        elif candidate_specificity == best_specificity:
            best_quality = max(best_quality, quality)

    return best_quality if best_specificity[0] >= 0 else None


def accepts_media_type(accept_header: str | None, media_type: str, *, explicit_only: bool = False) -> bool:
    """
    Return whether an Accept header permits a media type.
    """
    quality = _media_type_quality(accept_header, media_type, explicit_only=explicit_only)
    return quality is not None and quality > 0


def negotiate_media_type(
    accept_header: str | None,
    available: tuple[str, ...],
    *,
    default: str,
    explicit_only: frozenset[str] = frozenset(),
) -> str | None:
    """
    Select the highest-quality available representation.

    The order of available media types is the server preference for ties.
    """
    if default not in available:
        raise ValueError("default media type must be available")
    if accept_header is None:
        return default

    selected: str | None = None
    selected_quality = 0.0
    for media_type in available:
        quality = _media_type_quality(
            accept_header,
            media_type,
            explicit_only=media_type in explicit_only,
        )
        if quality is not None and quality > selected_quality:
            selected = media_type
            selected_quality = quality
    return selected


def negotiate_api_media_type(accept_header: str | None, *, allow_cbor: bool = True) -> str | None:
    """
    Select an API success representation.

    JSON is the default and wins ties. CBOR is optional and must be requested
    explicitly; wildcards never opt a client into the binary representation.
    """
    json_candidates = (JSON_MEDIA_TYPE, f"{JSON_MEDIA_TYPE}; charset=utf-8")
    available = (*json_candidates, CBOR_MEDIA_TYPE) if allow_cbor else json_candidates
    explicit_only = frozenset({CBOR_MEDIA_TYPE}) if allow_cbor else frozenset()
    return negotiate_media_type(
        accept_header,
        available,
        default=JSON_MEDIA_TYPE,
        explicit_only=explicit_only,
    )


def negotiate_problem_media_type(accept_header: str | None) -> str:
    """
    Select an error representation without replacing the original error status.

    RFC 9457 explicitly permits application/problem+json when it was not listed
    in Accept. CBOR is used only when application/cbor is explicitly preferred;
    otherwise JSON Problem Details is the interoperable fallback.
    """
    candidates = (PROBLEM_JSON_MEDIA_TYPE, f"{PROBLEM_JSON_MEDIA_TYPE}; charset=utf-8")
    json_choice: str | None = None
    json_quality = 0.0
    for candidate in candidates:
        quality = _media_type_quality(accept_header, candidate)
        if quality is not None and quality > json_quality:
            json_choice = candidate
            json_quality = quality
    cbor_quality = _media_type_quality(accept_header, CBOR_MEDIA_TYPE, explicit_only=True) or 0.0
    if cbor_quality > json_quality:
        return CBOR_MEDIA_TYPE
    return json_choice or PROBLEM_JSON_MEDIA_TYPE


def content_type_matches(content_type: str, media_type: str) -> bool:
    """
    Return whether Content-Type matches a media type, ignoring parameters.
    """
    return normalize_media_type(content_type) == normalize_media_type(media_type)


def content_type_is_allowed(content_type: str, allowed: frozenset[str]) -> bool:
    """
    Return whether Content-Type is in an allowed set.
    """
    return normalize_media_type(content_type) in allowed
