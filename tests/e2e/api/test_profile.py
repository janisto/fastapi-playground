"""Firestore-emulator evidence for the portable profile lifecycle."""

import asyncio

from fastapi.testclient import TestClient

from app.core.firebase import close_async_firestore_client
from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
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

    deleted = e2e_client.delete(PROFILE_PATH)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert e2e_client.get(PROFILE_PATH).json()["code"] == "profile_not_found"


async def test_concurrent_emulator_creates_and_deletes_have_exact_outcomes() -> None:
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
        assert sum(result is None for result in delete_results) == 1
        assert sum(isinstance(result, ProfileNotFoundError) for result in delete_results) == 1
    finally:
        close_async_firestore_client()
