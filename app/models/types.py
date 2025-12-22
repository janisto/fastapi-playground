"""
Shared Pydantic type aliases for validation and normalization.
"""

from typing import Annotated

from pydantic import AfterValidator, EmailStr, StringConstraints


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
