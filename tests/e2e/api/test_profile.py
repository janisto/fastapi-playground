"""Firestore-emulator evidence for the portable profile lifecycle."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.core.firebase import close_async_firestore_client
from app.exceptions import ProfileAlreadyExistsError, ProfileDependencyError, ProfileNotFoundError
from app.models.profile import Profile, ProfileCreate
from app.services.profile import ProfileService

PROFILE_PATH = "/v1/profile"


def _payload(first_name: str = "E2E") -> dict[str, object]:
    return {
        "firstName": first_name,
        "lastName": "User",
        "contactEmail": " E2E@EXAMPLE.COM ",
        "phoneNumber": " +358401234567 ",
        "termsAccepted": True,
    }


def test_profile_crud_noop_and_duplicate_preservation(e2e_client: TestClient) -> None:
    created = e2e_client.post(PROFILE_PATH, json=_payload())
    assert created.status_code == 201
    original = created.json()
    assert original["id"] == "e2e-user"
    assert original["contactEmail"] == "E2E@example.com"
    assert original["createdAt"] == original["updatedAt"]
    assert created.headers["Location"] == PROFILE_PATH

    duplicate = e2e_client.post(PROFILE_PATH, json=_payload("Replacement"))
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "profile_exists"
    assert e2e_client.get(PROFILE_PATH).json() == original

    noop = e2e_client.patch(PROFILE_PATH, json={"firstName": "E2E"})
    assert noop.status_code == 200
    assert noop.json() == original

    changed = e2e_client.patch(PROFILE_PATH, json={"marketingOptIn": True})
    assert changed.status_code == 200
    assert changed.json()["marketingOptIn"] is True
    assert changed.json()["createdAt"] == original["createdAt"]
    assert changed.json()["updatedAt"] > original["updatedAt"]

    opted_out = e2e_client.patch(PROFILE_PATH, json={"marketingOptIn": False})
    assert opted_out.status_code == 200
    expected = {**original, "updatedAt": opted_out.json()["updatedAt"]}
    assert opted_out.json() == expected
    assert opted_out.json()["updatedAt"] > changed.json()["updatedAt"]
    assert e2e_client.get(PROFILE_PATH).json() == expected

    deleted = e2e_client.delete(PROFILE_PATH)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert e2e_client.get(PROFILE_PATH).json()["code"] == "profile_not_found"


async def test_concurrent_emulator_operations_preserve_atomicity_and_recover_from_contention() -> None:
    service = ProfileService()
    create = ProfileCreate.model_validate(_payload("Race"), strict=True)
    try:
        create_results = await asyncio.gather(
            service.create_profile("race-user", create),
            service.create_profile("race-user", create),
            return_exceptions=True,
        )
        assert sum(isinstance(result, Profile) for result in create_results) == 1
        assert sum(isinstance(result, ProfileAlreadyExistsError) for result in create_results) == 1

        delete_results = await asyncio.gather(
            service.delete_profile("race-user"),
            service.delete_profile("race-user"),
            return_exceptions=True,
        )
        assert all(
            result is None or isinstance(result, ProfileNotFoundError | ProfileDependencyError)
            for result in delete_results
        )
        successful_deletes = sum(result is None for result in delete_results)
        assert successful_deletes <= 1
        if successful_deletes == 0:
            # Emulator lock contention can exhaust both SDK transactions without a commit.
            assert all(isinstance(result, ProfileDependencyError) for result in delete_results)
            original = next(result for result in create_results if isinstance(result, Profile))
            assert await service.get_profile("race-user") == original
            await service.delete_profile("race-user")
        with pytest.raises(ProfileNotFoundError):
            await service.get_profile("race-user")
        with pytest.raises(ProfileNotFoundError):
            await service.delete_profile("race-user")
    finally:
        close_async_firestore_client()


def test_real_emulator_token_drives_profile_crud_without_adc(
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
) -> None:
    import httpx2

    from app.main import app

    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/must-not-read/obsolete-key.json")
    adc = mocker.patch("google.auth.default", side_effect=AssertionError("ADC lookup"))
    signup = httpx2.post(
        "http://127.0.0.1:7010/identitytoolkit.googleapis.com/v1/accounts:signUp",
        params={"key": "demo-test"},
        json={"returnSecureToken": True},
        timeout=5,
    )
    assert signup.status_code == 200
    identity = signup.json()
    headers = {"Authorization": f"Bearer {identity['idToken']}"}
    with TestClient(app) as client:
        assert client.get(PROFILE_PATH).status_code == 401
        created = client.post(PROFILE_PATH, json=_payload("Local"), headers=headers)
        assert created.status_code == 201
        assert created.json()["id"] == identity["localId"]
        assert client.get(PROFILE_PATH, headers=headers).json() == created.json()
        changed = client.patch(PROFILE_PATH, json={"marketingOptIn": True}, headers=headers)
        assert changed.status_code == 200
        assert changed.json()["marketingOptIn"] is True
        assert changed.json()["createdAt"] == created.json()["createdAt"]
        assert changed.json()["updatedAt"] > created.json()["updatedAt"]
        assert client.delete(PROFILE_PATH, headers=headers).status_code == 204
        assert client.get(PROFILE_PATH, headers=headers).json()["code"] == "profile_not_found"
    adc.assert_not_called()
