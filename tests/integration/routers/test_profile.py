"""
Integration tests for profile endpoints.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from tests.helpers.profiles import make_profile, make_profile_payload_dict

BASE_URL = "/profile"


class TestCreateProfile:
    """
    Tests for POST /profile/.
    """

    def test_returns_201_on_success(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify successful profile creation returns 201.
        """
        mock_profile_service.create_profile.return_value = make_profile()

        response = client.post(f"{BASE_URL}/", json=make_profile_payload_dict())

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Profile created successfully"
        assert body["profile"] is not None
        mock_profile_service.create_profile.assert_awaited_once()

    def test_returns_409_when_duplicate(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify duplicate profile returns 409 Conflict.
        """
        mock_profile_service.create_profile.side_effect = ProfileAlreadyExistsError()

        response = client.post(f"{BASE_URL}/", json=make_profile_payload_dict())

        assert response.status_code == 409
        assert response.json()["detail"] == "Profile already exists"

    def test_returns_500_on_unexpected_error(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unexpected service error returns 500.
        """
        mock_profile_service.create_profile.side_effect = RuntimeError("Database connection failed")

        response = client.post(f"{BASE_URL}/", json=make_profile_payload_dict())

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to create profile"

    def test_returns_401_without_auth(
        self,
        client: TestClient,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unauthenticated request returns 401.
        """
        response = client.post(f"{BASE_URL}/", json=make_profile_payload_dict())

        assert response.status_code == 401

    def test_returns_422_with_invalid_email(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify invalid email returns 422 validation error.
        """
        payload = make_profile_payload_dict(email="not-an-email")

        response = client.post(f"{BASE_URL}/", json=payload)

        assert response.status_code == 422

    def test_returns_422_with_missing_required_field(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify missing required field returns 422 validation error.
        """
        payload = make_profile_payload_dict(omit=["firstname"])

        response = client.post(f"{BASE_URL}/", json=payload)

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "missing_field",
        ["firstname", "lastname", "email", "phone_number", "terms"],
    )
    def test_returns_422_for_missing_fields(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
        missing_field: str,
    ) -> None:
        """
        Verify missing required fields return 422.
        """
        payload = make_profile_payload_dict(omit=[missing_field])

        response = client.post(f"{BASE_URL}/", json=payload)

        assert response.status_code == 422
        body = response.json()
        assert any(missing_field in str(err.get("loc", [])) for err in body["detail"])


class TestGetProfile:
    """
    Tests for GET /profile/.
    """

    def test_returns_200_when_exists(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify getting existing profile returns 200.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(f"{BASE_URL}/")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["profile"] is not None
        mock_profile_service.get_profile.assert_awaited_once()

    def test_returns_404_when_not_found(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify missing profile returns 404.
        """
        mock_profile_service.get_profile.side_effect = ProfileNotFoundError()

        response = client.get(f"{BASE_URL}/")

        assert response.status_code == 404
        assert response.json()["detail"] == "Profile not found"

    def test_returns_500_on_unexpected_error(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unexpected service error returns 500.
        """
        mock_profile_service.get_profile.side_effect = RuntimeError("Database connection failed")

        response = client.get(f"{BASE_URL}/")

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to retrieve profile"

    def test_returns_401_without_auth(
        self,
        client: TestClient,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unauthenticated request returns 401.
        """
        response = client.get(f"{BASE_URL}/")

        assert response.status_code == 401


class TestUpdateProfile:
    """
    Tests for PATCH /profile/.
    """

    def test_returns_200_on_success(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify successful profile update returns 200.
        """
        mock_profile_service.update_profile.return_value = make_profile(firstname="Updated")

        response = client.patch(f"{BASE_URL}/", json={"firstname": "Updated"})

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Profile updated successfully"
        mock_profile_service.update_profile.assert_awaited_once()

    def test_returns_404_when_not_found(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify updating missing profile returns 404.
        """
        mock_profile_service.update_profile.side_effect = ProfileNotFoundError()

        response = client.patch(f"{BASE_URL}/", json={"firstname": "Updated"})

        assert response.status_code == 404
        assert response.json()["detail"] == "Profile not found"

    def test_returns_500_on_unexpected_error(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unexpected service error returns 500.
        """
        mock_profile_service.update_profile.side_effect = RuntimeError("Database connection failed")

        response = client.patch(f"{BASE_URL}/", json={"firstname": "Updated"})

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to update profile"

    def test_returns_401_without_auth(
        self,
        client: TestClient,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unauthenticated request returns 401.
        """
        response = client.patch(f"{BASE_URL}/", json={"firstname": "Updated"})

        assert response.status_code == 401

    def test_allows_partial_update(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify partial update with single field works.
        """
        mock_profile_service.update_profile.return_value = make_profile(lastname="NewLast")

        response = client.patch(f"{BASE_URL}/", json={"lastname": "NewLast"})

        assert response.status_code == 200

    def test_allows_empty_update(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify empty update body is accepted.
        """
        mock_profile_service.update_profile.return_value = make_profile()

        response = client.patch(f"{BASE_URL}/", json={})

        assert response.status_code == 200


class TestDeleteProfile:
    """
    Tests for DELETE /profile/.
    """

    def test_returns_200_on_success(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify successful profile deletion returns 200.
        """
        mock_profile_service.delete_profile.return_value = make_profile()

        response = client.delete(f"{BASE_URL}/")

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Profile deleted successfully"
        mock_profile_service.delete_profile.assert_awaited_once()

    def test_returns_404_when_not_found(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify deleting missing profile returns 404.
        """
        mock_profile_service.delete_profile.side_effect = ProfileNotFoundError()

        response = client.delete(f"{BASE_URL}/")

        assert response.status_code == 404
        assert response.json()["detail"] == "Profile not found"

    def test_returns_500_on_unexpected_error(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unexpected service error returns 500.
        """
        mock_profile_service.delete_profile.side_effect = RuntimeError("Database connection failed")

        response = client.delete(f"{BASE_URL}/")

        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to delete profile"

    def test_returns_401_without_auth(
        self,
        client: TestClient,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unauthenticated request returns 401.
        """
        response = client.delete(f"{BASE_URL}/")

        assert response.status_code == 401


class TestProfileResponseFormat:
    """
    Tests for profile response format.
    """

    def test_response_includes_profile_data(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify response includes complete profile data.
        """
        profile = make_profile(
            firstname="John",
            lastname="Doe",
            email="john@example.com",
        )
        mock_profile_service.get_profile.return_value = profile

        response = client.get(f"{BASE_URL}/")

        body = response.json()
        assert body["profile"]["firstname"] == "John"
        assert body["profile"]["lastname"] == "Doe"
        assert body["profile"]["email"] == "john@example.com"

    def test_response_includes_timestamps(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify response includes timestamp fields.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(f"{BASE_URL}/")

        body = response.json()
        assert "created_at" in body["profile"]
        assert "updated_at" in body["profile"]
