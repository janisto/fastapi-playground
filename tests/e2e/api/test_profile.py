"""
E2E tests for profile endpoints against Firebase emulators.

These tests verify the complete flow including real Firestore operations.
Requires Firebase emulators to be running.
"""

from fastapi import status
from fastapi.testclient import TestClient

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
            "firstname": "E2E",
            "lastname": "User",
            "email": "E2E@EXAMPLE.COM",
            "phone_number": "+358401234567",
            "marketing": False,
            "terms": True,
        }

        created = e2e_client.post(BASE_URL, json=profile)
        assert created.status_code == status.HTTP_201_CREATED
        assert created.json()["id"] == "e2e-user"
        assert created.json()["email"] == "e2e@example.com"

        retrieved = e2e_client.get(BASE_URL)
        assert retrieved.status_code == status.HTTP_200_OK
        assert retrieved.json()["firstname"] == "E2E"

        updated = e2e_client.patch(BASE_URL, json={"firstname": "Updated", "marketing": True})
        assert updated.status_code == status.HTTP_200_OK
        assert updated.json()["firstname"] == "Updated"
        assert updated.json()["marketing"] is True

        deleted = e2e_client.delete(BASE_URL)
        assert deleted.status_code == status.HTTP_204_NO_CONTENT

        missing = e2e_client.get(BASE_URL)
        assert missing.status_code == status.HTTP_404_NOT_FOUND
