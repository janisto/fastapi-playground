"""
Shared Pydantic type aliases for validation and normalization.
"""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, EmailStr, PlainSerializer, StringConstraints


def _serialize_datetime_ms(value: datetime) -> str:
    """
    Serialize datetime with explicit milliseconds (.000Z format).

    Both `2025-01-15T10:30:00Z` and `2025-01-15T10:30:00.000Z` are valid ISO 8601,
    but this ensures consistent millisecond precision across all API responses.
    """
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


# UTC datetime with consistent .000Z milliseconds format
UtcDatetime = Annotated[datetime, PlainSerializer(_serialize_datetime_ms)]


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

# ISO 639-1 language codes (e.g., "en", "fi")
LanguageCode = Annotated[
    str,
    StringConstraints(min_length=2, max_length=2, pattern=r"^[a-z]{2}$"),
]

# ISO 3166-1 alpha-2 country codes (e.g., "US", "FI")
CountryCode = Annotated[
    str,
    StringConstraints(min_length=2, max_length=2, pattern=r"^[A-Z]{2}$"),
]
