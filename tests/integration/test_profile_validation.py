"""Validation tests for profile endpoints focusing on request body schema.

These tests build malformed payloads via helpers to trigger 422 responses
from FastAPI/Pydantic before hitting service logic.
"""

import pytest
from fastapi.testclient import TestClient

from tests.helpers.profiles import make_profile_payload_dict


@pytest.mark.parametrize(
    "missing_field",
    [
        "firstname",
        "lastname",
        "email",
        "phone_number",
        "terms",
    ],
)
def test_create_profile_missing_required_field_returns_422(
    client: TestClient, with_fake_user: None, missing_field: str
) -> None:
    payload = make_profile_payload_dict(omit=[missing_field])

    res = client.post("/profile/", json=payload)

    assert res.status_code == 422
    # Ensure the validation error mentions the missing field
    body = res.json()
    assert body["detail"]
    assert any(missing_field in str(err.get("loc", [])) for err in body["detail"])  # type: ignore[index]


def test_create_profile_missing_entire_body_returns_422(client: TestClient, with_fake_user: None) -> None:
    res = client.post("/profile/", json={})

    assert res.status_code == 422
    body = res.json()
    # At least one required field error should be present
    assert body["detail"] and isinstance(body["detail"], list)


def test_create_profile_invalid_email_returns_422(client: TestClient, with_fake_user: None) -> None:
    payload = make_profile_payload_dict(overrides={"email": "not-an-email"})
    res = client.post("/profile/", json=payload)
    assert res.status_code == 422
    body = res.json()
    assert any("email" in str(err.get("loc", [])) for err in body["detail"])  # type: ignore[index]


@pytest.mark.parametrize(
    "bad_phone",
    [
        "abcd",  # non-digits
        "+",  # just plus
        "+1-234",  # contains dash
        "(123)456",  # parentheses
        "+001234",  # leading 0 after plus not allowed by pattern
        "01",  # leading 0 without plus
        "0",  # single zero
    ],
)
def test_create_profile_invalid_phone_returns_422(client: TestClient, with_fake_user: None, bad_phone: str) -> None:
    payload = make_profile_payload_dict(overrides={"phone_number": bad_phone})
    res = client.post("/profile/", json=payload)
    assert res.status_code == 422
    body = res.json()
    assert any("phone_number" in str(err.get("loc", [])) for err in body["detail"])  # type: ignore[index]


@pytest.mark.parametrize("field", ["marketing", "terms"])
@pytest.mark.parametrize("bad_value", [{}, []])
def test_create_profile_non_boolean_fields_return_422(
    client: TestClient, with_fake_user: None, field: str, bad_value: object
) -> None:
    payload = make_profile_payload_dict(overrides={field: bad_value})
    res = client.post("/profile/", json=payload)
    assert res.status_code == 422
    body = res.json()
    assert any(field in str(err.get("loc", [])) for err in body["detail"])  # type: ignore[index]


# --- PUT /profile/ invalid partial updates ---


def test_update_profile_invalid_email_returns_422(client: TestClient, with_fake_user: None) -> None:
    res = client.put("/profile/", json={"email": "not-an-email"})
    assert res.status_code == 422
    body = res.json()
    assert any("email" in str(err.get("loc", [])) for err in body["detail"])  # type: ignore[index]


@pytest.mark.parametrize(
    "bad_phone",
    [
        "abcd",
        "+",
        "+1-234",
        "(123)456",
        "+001234",
        "01",
        "0",
    ],
)
def test_update_profile_invalid_phone_returns_422(client: TestClient, with_fake_user: None, bad_phone: str) -> None:
    res = client.put("/profile/", json={"phone_number": bad_phone})
    assert res.status_code == 422
    body = res.json()
    assert any("phone_number" in str(err.get("loc", [])) for err in body["detail"])  # type: ignore[index]


@pytest.mark.parametrize("field", ["marketing", "terms"])
@pytest.mark.parametrize("bad_value", [{}, []])
def test_update_profile_non_boolean_fields_return_422(
    client: TestClient, with_fake_user: None, field: str, bad_value: object
) -> None:
    res = client.put("/profile/", json={field: bad_value})
    assert res.status_code == 422
    body = res.json()
    assert any(field in str(err.get("loc", [])) for err in body["detail"])  # type: ignore[index]


@pytest.mark.parametrize("field", ["firstname", "lastname"])
@pytest.mark.parametrize(
    "bad_value",
    [
        "",  # too short
        "x" * 101,  # too long
        42,  # wrong type
    ],
)
def test_update_profile_invalid_name_fields_return_422(
    client: TestClient, with_fake_user: None, field: str, bad_value: object
) -> None:
    res = client.put("/profile/", json={field: bad_value})
    assert res.status_code == 422
    body = res.json()
    assert any(field in str(err.get("loc", [])) for err in body["detail"])  # type: ignore[index]


def test_create_profile_rejects_extra_keys(client: TestClient, with_fake_user: None) -> None:
    payload = make_profile_payload_dict(overrides={"unexpected": "value"})
    res = client.post("/profile/", json=payload)
    assert res.status_code == 422
    body = res.json()
    errors = body["detail"]
    assert any(
        "unexpected" in str(err.get("loc", [])) or str(err.get("type", "")).endswith("extra_forbidden")
        for err in errors
    )


def test_update_profile_rejects_extra_keys(client: TestClient, with_fake_user: None) -> None:
    res = client.put("/profile/", json={"unexpected": "value"})
    assert res.status_code == 422
    body = res.json()
    errors = body["detail"]
    assert any(
        "unexpected" in str(err.get("loc", [])) or str(err.get("type", "")).endswith("extra_forbidden")
        for err in errors
    )
