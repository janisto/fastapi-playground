"""
E2E tests for profile endpoints against Firebase emulators.

These tests verify the complete flow including real Firestore operations.
Requires Firebase emulators to be running.
"""

import asyncio

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.core.firebase import close_async_firestore_client
from app.exceptions import ProfileAlreadyExistsError
from app.models.profile import Profile
from app.services.profile import ProfileService
from tests.helpers.profiles import make_profile_create

BASE_URL = "/v1/profile"


class TestProfileE2EFlow:
    """
    End-to-end tests for profile CRUD operations.

    These tests use real Firebase emulators and verify data persistence.
    Note: Auth is still mocked since we need valid Firebase tokens.
    """

    def test_profile_crud_flow(self, e2e_client: TestClient) -> None:
        """
        Persist, retrieve, update, and delete a profile through the API.
        """
        profile = {
            "first_name": "E2E",
            "last_name": "User",
            "email": "E2E@EXAMPLE.COM",
            "phone_number": "+358401234567",
            "marketing": False,
            "terms": True,
        }

        created = e2e_client.post(BASE_URL, json=profile)
        assert created.status_code == status.HTTP_201_CREATED
        created_body = created.json()
        assert created_body["id"] == "e2e-user"
        assert created_body["email"] == "e2e@example.com"

        retrieved = e2e_client.get(BASE_URL)
        assert retrieved.status_code == status.HTTP_200_OK
        assert retrieved.json()["first_name"] == "E2E"

        updated = e2e_client.patch(BASE_URL, json={"first_name": "Updated", "marketing": True})
        assert updated.status_code == status.HTTP_200_OK
        updated_body = updated.json()
        assert updated_body["first_name"] == "Updated"
        assert updated_body["last_name"] == "User"
        assert updated_body["email"] == "e2e@example.com"
        assert updated_body["marketing"] is True
        assert updated_body["created_at"] == created_body["created_at"]

        deleted = e2e_client.delete(BASE_URL)
        assert deleted.status_code == status.HTTP_204_NO_CONTENT

        missing = e2e_client.get(BASE_URL)
        assert missing.status_code == status.HTTP_404_NOT_FOUND

    def test_duplicate_create_preserves_original_profile(self, e2e_client: TestClient) -> None:
        """
        Reject a duplicate create without overwriting the existing document.
        """
        original = {
            "first_name": "Original",
            "last_name": "User",
            "email": "original@example.com",
            "phone_number": "+358401234567",
            "marketing": False,
            "terms": True,
        }
        replacement = {**original, "first_name": "Replacement"}

        assert e2e_client.post(BASE_URL, json=original).status_code == status.HTTP_201_CREATED
        duplicate = e2e_client.post(BASE_URL, json=replacement)

        assert duplicate.status_code == status.HTTP_409_CONFLICT
        retrieved = e2e_client.get(BASE_URL)
        assert retrieved.status_code == status.HTTP_200_OK
        assert retrieved.json()["first_name"] == "Original"

    @pytest.mark.parametrize(
        ("method", "payload"),
        [
            ("patch", {"first_name": "Missing"}),
            ("delete", None),
        ],
    )
    def test_missing_profile_mutations_return_not_found(
        self,
        e2e_client: TestClient,
        method: str,
        payload: dict[str, str] | None,
    ) -> None:
        """
        Return 404 when a transaction targets a missing profile.
        """
        response = e2e_client.request(method, BASE_URL, json=payload)

        assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_concurrent_profile_creates_have_one_winner() -> None:
    """
    Verify the Firestore transaction prevents concurrent duplicate creation.
    """
    service = ProfileService()
    profile_data = make_profile_create(email="race@example.com")

    try:
        results = await asyncio.gather(
            service.create_profile("race-user", profile_data),
            service.create_profile("race-user", profile_data),
            return_exceptions=True,
        )
    finally:
        close_async_firestore_client()

    profiles = [result for result in results if isinstance(result, Profile)]
    conflicts = [result for result in results if isinstance(result, ProfileAlreadyExistsError)]
    assert len(profiles) == 1
    assert len(conflicts) == 1
