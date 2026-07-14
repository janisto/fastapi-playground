"""
HTTP media-type negotiation for API responses and request bodies.

Success negotiation honors RFC 9110 Accept ranges strictly. Error negotiation
is best effort: it preserves the original error status and falls back to RFC
9457 JSON Problem Details when the requested representation is unavailable.
"""

import re

CBOR_MEDIA_TYPE = "application/cbor"
JSON_MEDIA_TYPE = "application/json"
PROBLEM_JSON = "application/problem+json"
SCHEMA_JSON_MEDIA_TYPE = "application/schema+json"

ALLOWED_CONTENT_TYPES = frozenset({JSON_MEDIA_TYPE, CBOR_MEDIA_TYPE})

_QVALUE_PATTERN = re.compile(r"(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)\Z")


def normalize_media_type(media_type: str) -> str:
    """
    Normalize a media type for case-insensitive comparison.
    """
    return media_type.split(";", maxsplit=1)[0].strip().lower()


def _parse_qvalue(params: list[str]) -> float | None:
    """
    Parse an RFC 9110 quality value for a parameter-free representation.

    The q parameter is recognized regardless of ordering. Any other non-empty
    parameter constrains the media range and cannot match these representations.
    """
    quality = 1.0
    qvalue_seen = False
    has_media_parameter = False
    for raw_param in params:
        param = raw_param.strip()
        if not param:
            continue
        if param.lower().startswith("q="):
            if qvalue_seen:
                return None
            raw_quality = param[2:]
            if _QVALUE_PATTERN.fullmatch(raw_quality) is None:
                return None
            quality = float(raw_quality)
            qvalue_seen = True
        else:
            has_media_parameter = True
    return None if has_media_parameter else quality


def _media_range_specificity(range_type: str, target: str, target_parts: list[str]) -> int | None:
    """
    Return the RFC 9110 specificity of a matching media range.
    """
    if range_type == target:
        return 2
    if range_type == "*/*":
        return 0
    range_parts = range_type.split("/")
    if len(range_parts) == 2 and range_parts[1] == "*" and range_parts[0] == target_parts[0]:
        return 1
    return None


def _media_type_quality(accept_header: str, media_type: str, *, explicit_only: bool = False) -> float | None:
    """
    Return the effective quality of a media type, or None when it is not listed.

    The most specific matching range wins, so an exact q=0 exclusion overrides
    broader wildcards. When explicit_only is true, wildcards do not match.
    """
    if not accept_header:
        return None

    target = normalize_media_type(media_type)
    target_parts = target.split("/")
    best_specificity = -1
    best_quality = 0.0

    for raw_item in accept_header.split(","):
        item = raw_item.strip()
        if not item:
            continue

        parts = item.split(";")
        range_type = normalize_media_type(parts[0])
        quality = _parse_qvalue(parts[1:])
        if quality is None or "/" not in range_type:
            continue

        specificity = _media_range_specificity(range_type, target, target_parts)
        if specificity is None or (explicit_only and specificity < 2):
            continue
        if specificity > best_specificity:
            best_specificity = specificity
            best_quality = quality
        elif specificity == best_specificity:
            best_quality = max(best_quality, quality)

    return best_quality if best_specificity >= 0 else None


def accepts_media_type(accept_header: str, media_type: str, *, explicit_only: bool = False) -> bool:
    """
    Return whether an Accept header permits a media type.
    """
    quality = _media_type_quality(accept_header, media_type, explicit_only=explicit_only)
    return quality is not None and quality > 0


def negotiate_media_type(
    accept_header: str,
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
    if not accept_header:
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


def negotiate_api_media_type(accept_header: str, *, allow_cbor: bool = True) -> str | None:
    """
    Select an API success representation.

    JSON is the default and wins ties. CBOR is optional and must be requested
    explicitly; wildcards never opt a client into the binary representation.
    """
    available = (JSON_MEDIA_TYPE, CBOR_MEDIA_TYPE) if allow_cbor else (JSON_MEDIA_TYPE,)
    explicit_only = frozenset({CBOR_MEDIA_TYPE}) if allow_cbor else frozenset()
    return negotiate_media_type(
        accept_header,
        available,
        default=JSON_MEDIA_TYPE,
        explicit_only=explicit_only,
    )


def negotiate_problem_media_type(accept_header: str) -> str:
    """
    Select an error representation without replacing the original error status.

    RFC 9457 explicitly permits application/problem+json when it was not listed
    in Accept. CBOR is used only when application/cbor is explicitly preferred;
    otherwise JSON Problem Details is the interoperable fallback.
    """
    explicit_problem_json_quality = _media_type_quality(accept_header, PROBLEM_JSON, explicit_only=True)
    if explicit_problem_json_quality is None:
        json_qualities = (
            _media_type_quality(accept_header, PROBLEM_JSON),
            _media_type_quality(accept_header, JSON_MEDIA_TYPE),
        )
        json_quality = max((quality for quality in json_qualities if quality is not None), default=0.0)
    else:
        json_quality = explicit_problem_json_quality

    cbor_quality = _media_type_quality(accept_header, CBOR_MEDIA_TYPE, explicit_only=True) or 0.0
    if cbor_quality > json_quality:
        return CBOR_MEDIA_TYPE
    return PROBLEM_JSON


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
