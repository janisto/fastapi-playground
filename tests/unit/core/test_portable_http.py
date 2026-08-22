"""Adversarial tests for the portable parser and negotiation boundary."""

import math
from typing import cast

import cbor2
import pytest

from app.core.content_negotiation import (
    CBOR_MEDIA_TYPE,
    JSON_MEDIA_TYPE,
    PROBLEM_JSON_MEDIA_TYPE,
    negotiate_api_media_type,
    negotiate_problem_media_type,
)
from app.core.portable_http import parse_query_string, parse_strict_cbor, parse_strict_json, validate_closed_query
from app.core.problems import PortableProblem


@pytest.mark.parametrize(
    "payload",
    [
        b'{"name":"Ada","name":"Grace"}',
        b'{"name":"Ada"} trailing',
        b"\xef\xbb\xbf{}",
        b'{"name":"\xff"}',
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":"\\ud800"}',
    ],
)
def test_strict_json_rejects_ambiguous_or_nonportable_documents(payload: bytes) -> None:
    with pytest.raises(PortableProblem) as captured:
        parse_strict_json(payload)
    assert captured.value.code == "invalid_request"


def test_strict_json_accepts_one_utf8_document() -> None:
    assert parse_strict_json('{"name":"Åda"}\n'.encode()) == {"name": "Åda"}


def test_strict_json_rejects_excessive_nesting_and_integer_length() -> None:
    for payload in (b"[" * 2000 + b"0" + b"]" * 2000, b'{"value":' + b"9" * 5000 + b"}"):
        with pytest.raises(PortableProblem, match="invalid_request"):
            parse_strict_json(payload)


def test_strict_cbor_rejects_duplicate_keys_and_trailing_items() -> None:
    duplicate = bytes.fromhex("a2616101616102")
    for payload in (duplicate, cbor2.dumps({"name": "Ada"}) + cbor2.dumps(1), b"\xa1"):
        with pytest.raises(PortableProblem) as captured:
            parse_strict_cbor(payload)
        assert captured.value.code == "invalid_request"


def test_well_formed_cbor_preserves_nonfinite_value_for_schema_validation() -> None:
    value = parse_strict_cbor(cbor2.dumps({"name": math.nan}))
    assert math.isnan(cast("dict[str, float]", value)["name"])


@pytest.mark.parametrize("query", [b"x=%", b"x=%0", b"x=%GG", b"x=%FF"])
def test_query_parser_rejects_malformed_percent_or_utf8(query: bytes) -> None:
    with pytest.raises(PortableProblem) as captured:
        parse_query_string(query)
    assert captured.value.code == "invalid_request"


def test_query_parser_rejects_duplicates_after_decoding() -> None:
    with pytest.raises(PortableProblem):
        parse_query_string(b"limit=1&%6cimit=2")


def test_closed_query_splits_malformed_and_typed_failures() -> None:
    with pytest.raises(PortableProblem) as unknown:
        validate_closed_query(b"other=1", frozenset({"limit"}))
    with pytest.raises(PortableProblem) as typed:
        validate_closed_query(b"limit=+1", frozenset({"limit"}))
    assert unknown.value.code == "invalid_request"
    assert typed.value.code == "validation_failed"


@pytest.mark.parametrize(
    ("accept", "expected"),
    [
        (None, JSON_MEDIA_TYPE),
        ("", None),
        ("*/*", JSON_MEDIA_TYPE),
        ("application/*", JSON_MEDIA_TYPE),
        ("application/cbor", CBOR_MEDIA_TYPE),
        ("application/json;q=0.5, application/cbor;q=0.9", CBOR_MEDIA_TYPE),
        ("application/json;q=0.9, application/cbor;q=0.9", JSON_MEDIA_TYPE),
        ("application/json; charset=UTF-8", "application/json; charset=utf-8"),
        ("application/json;q=0.5;charset=utf-8", "application/json; charset=utf-8"),
        (
            "application/json; charset=utf-8;q=1, application/json;q=0",
            "application/json; charset=utf-8",
        ),
        ("application/json; profile=x", None),
        ("application/json;q=0.5;profile=x", None),
        ("*/*;q=1, application/json;q=0", None),
        ("application/cbor;profile=x", None),
        ("application/json; charset =utf-8", None),
        ("application/json; charset= utf-8", None),
        ("application/json; q =0.5", None),
        ("application/json; q= 0.5", None),
        ("application/json;q=1.0000", None),
        ("application/json;q=.5", None),
        ('application/json;q="0.5"', None),
        ("application/json\xa0", None),
        ("application/json;\xa0q=1", None),
        ("application/cbor\xa0", None),
    ],
)
def test_success_negotiation_honors_specificity_qvalue_and_exact_cbor_opt_in(
    accept: str | None,
    expected: str | None,
) -> None:
    assert negotiate_api_media_type(accept) == expected


def test_problem_negotiation_preserves_error_with_json_fallback() -> None:
    assert negotiate_problem_media_type(None) == PROBLEM_JSON_MEDIA_TYPE
    assert negotiate_problem_media_type("application/json") == PROBLEM_JSON_MEDIA_TYPE
    assert negotiate_problem_media_type("text/plain") == PROBLEM_JSON_MEDIA_TYPE
    assert negotiate_problem_media_type("application/cbor;q=1, application/problem+json;q=0.5") == CBOR_MEDIA_TYPE
    assert negotiate_problem_media_type("application/json;q=1, application/cbor;q=0.5") == CBOR_MEDIA_TYPE
    assert negotiate_problem_media_type("application/cbor\xa0") == PROBLEM_JSON_MEDIA_TYPE
    assert (
        negotiate_problem_media_type("application/problem+json; charset=UTF-8")
        == "application/problem+json; charset=utf-8"
    )
