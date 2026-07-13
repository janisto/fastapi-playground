"""
Shared Pydantic type aliases for validation and normalization.
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, EmailStr, PlainSerializer, StringConstraints


def _serialize_datetime_ms(value: datetime) -> str:
    """
    Serialize datetime with explicit milliseconds (.000Z format).

    Both `2025-01-15T10:30:00Z` and `2025-01-15T10:30:00.000Z` are valid ISO 8601,
    but this ensures consistent millisecond precision across all API responses.
    """
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


def _normalize_utc_datetime(value: datetime) -> datetime:
    """
    Require timezone awareness and normalize values to UTC.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must include timezone information")
    return value.astimezone(UTC)


# UTC datetime with consistent .000Z milliseconds format
UtcDatetime = Annotated[
    datetime,
    AfterValidator(_normalize_utc_datetime),
    PlainSerializer(_serialize_datetime_ms),
]


def normalize_email(email: str) -> str:
    """
    Lowercase and strip email for consistent storage.
    """
    return email.lower().strip()


# Normalized email (lowercase, stripped)
NormalizedEmail = Annotated[EmailStr, AfterValidator(normalize_email)]

# E.164 phone number format (e.g., "+358401234567")
Phone = Annotated[
    str,
    StringConstraints(min_length=8, max_length=16, pattern=r"^\+[1-9]\d{6,14}$", strip_whitespace=True),
]
