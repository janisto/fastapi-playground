"""
Unit tests for shared type aliases.
"""

from datetime import UTC, datetime

import pytest
from pydantic import BaseModel, ValidationError

from app.models.types import CountryCode, LanguageCode, NormalizedEmail, Phone, UtcDatetime


class TestNormalizedEmail:
    """
    Tests for NormalizedEmail type alias.
    """

    def test_lowercases_email(self) -> None:
        """
        Verify email is lowercased.
        """

        class TestModel(BaseModel):
            email: NormalizedEmail

        result = TestModel(email="John.Doe@Example.COM")
        assert result.email == "john.doe@example.com"

    def test_strips_whitespace(self) -> None:
        """
        Verify leading/trailing whitespace is stripped.
        """

        class TestModel(BaseModel):
            email: NormalizedEmail

        result = TestModel(email="  user@example.com  ")
        assert result.email == "user@example.com"

    def test_invalid_email_raises(self) -> None:
        """
        Verify invalid email format raises ValidationError.
        """

        class TestModel(BaseModel):
            email: NormalizedEmail

        with pytest.raises(ValidationError):
            TestModel(email="not-an-email")


class TestPhone:
    """
    Tests for Phone type alias (E.164 format).
    """

    @pytest.mark.parametrize(
        "valid_phone",
        [
            "+358401234567",
            "+1234567890",
            "+12345678901234",
        ],
    )
    def test_valid_phones(self, valid_phone: str) -> None:
        """
        Verify valid E.164 phone numbers are accepted.
        """

        class TestModel(BaseModel):
            phone: Phone

        result = TestModel(phone=valid_phone)
        assert result.phone == valid_phone

    @pytest.mark.parametrize(
        "invalid_phone",
        [
            "invalid",
            "123456789",
            "+0123456789",
            "+1",
            "++358401234567",
        ],
    )
    def test_invalid_phone_raises(self, invalid_phone: str) -> None:
        """
        Verify invalid phone formats raise ValidationError.
        """

        class TestModel(BaseModel):
            phone: Phone

        with pytest.raises(ValidationError):
            TestModel(phone=invalid_phone)

    def test_strips_whitespace(self) -> None:
        """
        Verify leading/trailing whitespace is stripped.
        """

        class TestModel(BaseModel):
            phone: Phone

        result = TestModel(phone="  +358401234567  ")
        assert result.phone == "+358401234567"


class TestLanguageCode:
    """
    Tests for LanguageCode type alias (ISO 639-1).
    """

    @pytest.mark.parametrize("valid_code", ["en", "fi", "sv", "de"])
    def test_valid_language_codes(self, valid_code: str) -> None:
        """
        Verify valid ISO 639-1 codes are accepted.
        """

        class TestModel(BaseModel):
            lang: LanguageCode

        result = TestModel(lang=valid_code)
        assert result.lang == valid_code

    @pytest.mark.parametrize(
        "invalid_code",
        [
            "EN",
            "e",
            "eng",
            "12",
        ],
    )
    def test_invalid_language_code_raises(self, invalid_code: str) -> None:
        """
        Verify invalid language codes raise ValidationError.
        """

        class TestModel(BaseModel):
            lang: LanguageCode

        with pytest.raises(ValidationError):
            TestModel(lang=invalid_code)


class TestCountryCode:
    """
    Tests for CountryCode type alias (ISO 3166-1 alpha-2).
    """

    @pytest.mark.parametrize("valid_code", ["US", "FI", "DE", "GB"])
    def test_valid_country_codes(self, valid_code: str) -> None:
        """
        Verify valid ISO 3166-1 alpha-2 codes are accepted.
        """

        class TestModel(BaseModel):
            country: CountryCode

        result = TestModel(country=valid_code)
        assert result.country == valid_code

    @pytest.mark.parametrize(
        "invalid_code",
        [
            "us",
            "U",
            "USA",
            "12",
        ],
    )
    def test_invalid_country_code_raises(self, invalid_code: str) -> None:
        """
        Verify invalid country codes raise ValidationError.
        """

        class TestModel(BaseModel):
            country: CountryCode

        with pytest.raises(ValidationError):
            TestModel(country=invalid_code)


class TestUtcDatetime:
    """
    Tests for UtcDatetime type alias with .000Z milliseconds format.
    """

    def test_serializes_with_milliseconds(self) -> None:
        """
        Verify datetime is serialized with explicit .000Z milliseconds format.
        """

        class TestModel(BaseModel):
            timestamp: UtcDatetime

        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = TestModel(timestamp=dt)
        assert result.model_dump()["timestamp"] == "2025-01-15T10:30:00.000Z"

    def test_serializes_with_actual_milliseconds(self) -> None:
        """
        Verify datetime with microseconds is serialized with millisecond precision.
        """

        class TestModel(BaseModel):
            timestamp: UtcDatetime

        dt = datetime(2025, 1, 15, 10, 30, 0, 123456, tzinfo=UTC)
        result = TestModel(timestamp=dt)
        assert result.model_dump()["timestamp"] == "2025-01-15T10:30:00.123Z"

    def test_json_serialization(self) -> None:
        """
        Verify JSON output uses .000Z format.
        """

        class TestModel(BaseModel):
            timestamp: UtcDatetime

        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = TestModel(timestamp=dt)
        assert '"timestamp":"2025-01-15T10:30:00.000Z"' in result.model_dump_json()

    def test_preserves_full_precision(self) -> None:
        """
        Verify milliseconds from various microsecond values are calculated correctly.
        """

        class TestModel(BaseModel):
            timestamp: UtcDatetime

        test_cases = [
            (0, "000"),
            (1000, "001"),
            (500000, "500"),
            (999000, "999"),
        ]
        for microseconds, expected_ms in test_cases:
            dt = datetime(2025, 1, 15, 10, 30, 0, microseconds, tzinfo=UTC)
            result = TestModel(timestamp=dt)
            serialized = result.model_dump()["timestamp"]
            assert serialized.endswith(f".{expected_ms}Z"), f"Expected .{expected_ms}Z, got {serialized}"
