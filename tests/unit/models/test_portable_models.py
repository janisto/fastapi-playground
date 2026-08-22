"""Exact portable scalar and model tests."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from google.api_core.datetime_helpers import DatetimeWithNanoseconds
from pydantic import TypeAdapter, ValidationError

from app.models.profile import Profile, ProfileCreate, ProfileUpdate
from app.models.types import (
    BoundedName,
    ContactEmail,
    OpaqueId,
    PhoneNumber,
    SafeInteger,
    UTCDateTime,
    normalize_contact_email,
    normalize_phone,
    serialize_datetime_ms,
    validate_bounded_name,
)


@pytest.mark.parametrize("value", [" Ada", "Ada ", "\u00a0Ada", "Ada\u3000", "Ada\x7f", "", "a" * 101])
def test_bounded_name_rejects_exact_boundary_violations(value: str) -> None:
    with pytest.raises((ValueError, IndexError)):
        validate_bounded_name(value)


def test_name_preserves_unicode_without_normalization() -> None:
    value = "A\u030a"
    assert validate_bounded_name(value) == value


@pytest.mark.parametrize("value", ["A", "A" * 100, "𐀀" * 100, "Ada Lovelace"])
def test_bounded_name_accepts_exact_valid_boundaries(value: str) -> None:
    assert TypeAdapter(BoundedName).validate_python(value, strict=True) == value


def test_opaque_id_uses_unicode_scalar_boundaries() -> None:
    adapter = TypeAdapter(OpaqueId)
    assert adapter.validate_python("𐀀" * 128, strict=True) == "𐀀" * 128
    for value in ("", "x" * 129, "value\ud800"):
        with pytest.raises(ValidationError):
            adapter.validate_python(value, strict=True)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" Ada.Local@EXAMPLE.COM ", "Ada.Local@example.com"),
        ("\tA+b@example.co.uk\r", "A+b@example.co.uk"),
    ],
)
def test_contact_email_preserves_local_case_and_lowercases_domain(value: str, expected: str) -> None:
    assert normalize_contact_email(value) == expected


@pytest.mark.parametrize(
    "value",
    ["a@localhost", ".a@example.com", "a.@example.com", "a..b@example.com", "a@-example.com", "ä@example.com"],
)
def test_contact_email_rejects_values_outside_exact_ascii_grammar(value: str) -> None:
    with pytest.raises(ValueError, match="contact email is invalid"):
        normalize_contact_email(value)


def test_contact_email_exact_length_and_label_boundaries() -> None:
    adapter = TypeAdapter(ContactEmail)
    maximum = "L" * 64 + "@" + "a" * 63 + "." + "b" * 63 + "." + "c" * 61
    assert len(maximum) == 254
    assert adapter.validate_python(maximum, strict=True) == maximum
    for value in (
        "L" * 65 + "@example.com",
        maximum + "c",
        "a@" + "b" * 64 + ".com",
        "a@example..com",
    ):
        with pytest.raises(ValidationError):
            adapter.validate_python(value, strict=True)


def test_phone_strips_ascii_but_not_unicode_whitespace() -> None:
    assert normalize_phone("\t+358401234567 ") == "+358401234567"
    with pytest.raises(ValueError, match="phone number is invalid"):
        normalize_phone("\u00a0+358401234567")


def test_phone_accepts_and_rejects_adjacent_digit_boundaries() -> None:
    adapter = TypeAdapter(PhoneNumber)
    for value in ("+1234567", "+" + "9" * 15):
        assert adapter.validate_python(value, strict=True) == value
    for value in ("+123456", "+" + "9" * 16, "+01234567"):
        with pytest.raises(ValidationError):
            adapter.validate_python(value, strict=True)


def test_safe_integer_accepts_only_exact_json_integer_domain() -> None:
    adapter = TypeAdapter(SafeInteger)
    for value in (0, 9_007_199_254_740_991):
        assert adapter.validate_python(value, strict=True) == value
    for value in (-1, 9_007_199_254_740_992, True, 1.0):
        with pytest.raises(ValidationError):
            adapter.validate_python(value, strict=True)


def test_profile_create_accepts_only_camel_case_and_literal_terms() -> None:
    payload = {
        "firstName": "Ada",
        "lastName": "Lovelace",
        "contactEmail": "Ada@EXAMPLE.COM",
        "phoneNumber": "+358401234567",
        "termsAccepted": True,
    }
    profile = ProfileCreate.model_validate(payload, strict=True)
    assert profile.contact_email == "Ada@example.com"
    assert profile.marketing_opt_in is False
    for invalid in ({**payload, "termsAccepted": False}, {**payload, "first_name": "Ada"}, {**payload, "extra": 1}):
        with pytest.raises(ValidationError):
            ProfileCreate.model_validate(invalid, strict=True)


@pytest.mark.parametrize("payload", [{}, {"firstName": None}, {"id": "other"}, {"updatedAt": "x"}])
def test_profile_update_is_nonempty_closed_and_nonnull(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate(payload, strict=True)


def test_timestamp_serializer_uses_exact_milliseconds() -> None:
    assert serialize_datetime_ms(datetime(2026, 7, 30, 12, 0, 0, 123000, tzinfo=UTC)) == "2026-07-30T12:00:00.123Z"


def test_timestamp_normalizes_timezone_and_rejects_submilliseconds() -> None:
    adapter = TypeAdapter(UTCDateTime)
    value = datetime(2026, 7, 30, 14, 0, 0, 123000, tzinfo=timezone(timedelta(hours=2)))
    assert adapter.validate_python(value, strict=True) == datetime(2026, 7, 30, 12, 0, 0, 123000, tzinfo=UTC)
    for invalid in (
        datetime(2026, 7, 30, tzinfo=timezone(timedelta(0))).replace(tzinfo=None),
        datetime(2026, 7, 30, microsecond=1, tzinfo=UTC),
    ):
        with pytest.raises(ValidationError):
            adapter.validate_python(invalid, strict=True)


@pytest.mark.parametrize("timezone_value", [UTC, timezone(timedelta(hours=2))])
def test_timestamp_rejects_hidden_firestore_submillisecond_precision(timezone_value: timezone) -> None:
    adapter = TypeAdapter(UTCDateTime)
    exact_millisecond = DatetimeWithNanoseconds(
        2026,
        7,
        30,
        12,
        0,
        tzinfo=timezone_value,
        nanosecond=123_000_000,
    )
    hidden_submillisecond = DatetimeWithNanoseconds(
        2026,
        7,
        30,
        12,
        0,
        tzinfo=timezone_value,
        nanosecond=123_000_001,
    )

    assert adapter.validate_python(exact_millisecond, strict=True).microsecond == 123_000
    with pytest.raises(ValidationError, match="whole-millisecond precision"):
        adapter.validate_python(hidden_submillisecond, strict=True)


def test_profile_rejects_update_before_creation() -> None:
    with pytest.raises(ValidationError):
        Profile.model_validate(
            {
                "id": "principal",
                "firstName": "Ada",
                "lastName": "Lovelace",
                "contactEmail": "Ada@example.com",
                "phoneNumber": "+358401234567",
                "marketingOptIn": False,
                "termsAccepted": True,
                "createdAt": datetime(2026, 1, 2, tzinfo=UTC),
                "updatedAt": datetime(2026, 1, 1, tzinfo=UTC),
            },
            strict=True,
        )
