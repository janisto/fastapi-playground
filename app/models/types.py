"""
Portable scalar types and exact normalization rules.
"""

import re
from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field, PlainSerializer, StringConstraints, WithJsonSchema

SAFE_INTEGER_MAX = 9_007_199_254_740_991
_ASCII_WHITESPACE = "\t\n\v\f\r "
_EMAIL_LOCAL = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_{|}~.-]{1,64}\Z")
_DOMAIN_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
_PHONE = re.compile(r"\+[1-9][0-9]{6,14}\Z")
_ASCII_WHITESPACE_MIN = 0x0009
_ASCII_WHITESPACE_MAX = 0x000D
_UNICODE_WHITESPACE_RANGE_MIN = 0x2000
_UNICODE_WHITESPACE_RANGE_MAX = 0x200A
_CONTROL_C0_MAX = 0x001F
_CONTROL_C1_MIN = 0x007F
_CONTROL_C1_MAX = 0x009F
_SURROGATE_MIN = 0xD800
_SURROGATE_MAX = 0xDFFF
_NAME_MAX_LENGTH = 100
_OPAQUE_ID_MAX_LENGTH = 128
_EMAIL_MAX_LENGTH = 254
_MIN_DOMAIN_LABELS = 2


def serialize_datetime_ms(value: datetime) -> str:
    """Serialize a UTC instant with exactly three fractional digits."""
    utc = value.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def normalize_utc_datetime(value: datetime) -> datetime:
    """Require an aware whole-millisecond instant and normalize it to UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include timezone information")
    normalized = value.astimezone(UTC)
    if normalized.microsecond % 1000:
        raise ValueError("datetime must have whole-millisecond precision")
    return normalized


def truncate_clock_milliseconds(value: datetime) -> datetime:
    """Normalize an application-clock instant by discarding sub-milliseconds."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return a timezone-aware datetime")
    value = value.astimezone(UTC)
    return value.replace(microsecond=(value.microsecond // 1000) * 1000)


def _is_portable_whitespace(character: str) -> bool:
    code = ord(character)
    return (
        _ASCII_WHITESPACE_MIN <= code <= _ASCII_WHITESPACE_MAX
        or code in {0x0020, 0x0085, 0x00A0, 0x1680, 0x2028, 0x2029, 0x202F, 0x205F, 0x3000}
        or _UNICODE_WHITESPACE_RANGE_MIN <= code <= _UNICODE_WHITESPACE_RANGE_MAX
    )


def validate_bounded_name(value: str) -> str:
    """Apply the exact control, whitespace, and scalar-count rules for names."""
    if not 1 <= len(value) <= _NAME_MAX_LENGTH:
        raise ValueError("name length is invalid")
    if _is_portable_whitespace(value[0]) or _is_portable_whitespace(value[-1]):
        raise ValueError("name has surrounding whitespace")
    if any(
        ord(character) <= _CONTROL_C0_MAX
        or _CONTROL_C1_MIN <= ord(character) <= _CONTROL_C1_MAX
        or _SURROGATE_MIN <= ord(character) <= _SURROGATE_MAX
        for character in value
    ):
        raise ValueError("name contains a control character")
    return value


def validate_opaque_id(value: str) -> str:
    """Require one through 128 Unicode scalar values."""
    if not 1 <= len(value) <= _OPAQUE_ID_MAX_LENGTH or any(
        _SURROGATE_MIN <= ord(character) <= _SURROGATE_MAX for character in value
    ):
        raise ValueError("opaque identifier is invalid")
    return value


def normalize_contact_email(value: object) -> object:
    """Strip only ASCII whitespace and canonicalize only the domain."""
    if not isinstance(value, str):
        return value
    value = value.strip(_ASCII_WHITESPACE)
    if len(value) > _EMAIL_MAX_LENGTH or not value.isascii() or value.count("@") != 1:
        raise ValueError("contact email is invalid")
    local, domain = value.split("@")
    if _EMAIL_LOCAL.fullmatch(local) is None or local.startswith(".") or local.endswith(".") or ".." in local:
        raise ValueError("contact email is invalid")
    labels = domain.split(".")
    if len(labels) < _MIN_DOMAIN_LABELS or any(_DOMAIN_LABEL.fullmatch(label) is None for label in labels):
        raise ValueError("contact email is invalid")
    return f"{local}@{domain.lower()}"


def normalize_phone(value: object) -> object:
    """Strip only ASCII whitespace before exact E.164 validation."""
    if not isinstance(value, str):
        return value
    value = value.strip(_ASCII_WHITESPACE)
    if _PHONE.fullmatch(value) is None:
        raise ValueError("phone number is invalid")
    return value


SafeInteger = Annotated[int, Field(ge=0, le=SAFE_INTEGER_MAX, strict=True)]
OpaqueId = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=128),
    AfterValidator(validate_opaque_id),
]
BoundedName = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=100),
    AfterValidator(validate_bounded_name),
]
ContactEmail = Annotated[str, BeforeValidator(normalize_contact_email), StringConstraints(strict=True, max_length=254)]
PhoneNumber = Annotated[
    str,
    BeforeValidator(normalize_phone),
    StringConstraints(strict=True, pattern=r"^\+[1-9][0-9]{6,14}$"),
]
UTCDateTime = Annotated[
    datetime,
    AfterValidator(normalize_utc_datetime),
    PlainSerializer(serialize_datetime_ms, return_type=str, when_used="json"),
    WithJsonSchema(
        {
            "type": "string",
            "format": "date-time",
            "pattern": (
                r"^[0-9]{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])T"
                r"(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]\.[0-9]{3}Z$"
            ),
        },
        mode="serialization",
    ),
]
