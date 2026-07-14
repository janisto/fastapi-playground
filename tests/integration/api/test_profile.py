"""
Integration tests for profile endpoints.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from tests.helpers.profiles import make_profile, make_profile_payload_dict

BASE_URL = "/v1/profile"
PROFILE_FIELD_NAMES = {
    "id",
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "marketing",
    "terms",
    "created_at",
    "updated_at",
}


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

        response = client.post(BASE_URL, json=make_profile_payload_dict())

        assert response.status_code == 201
        body = response.json()
        assert "id" in body
        assert "first_name" in body
        assert response.headers.get("Location") == "/v1/profile"
        mock_profile_service.create_profile.assert_awaited_once()

    def test_response_does_not_embed_schema_metadata(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify POST /profile/ keeps schema metadata out of the representation.
        """
        mock_profile_service.create_profile.return_value = make_profile()

        response = client.post(BASE_URL, json=make_profile_payload_dict())

        body = response.json()
        assert "$schema" not in body

    def test_returns_describedby_link_header(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify POST /profile/ returns Link header with describedBy.
        """
        mock_profile_service.create_profile.return_value = make_profile()

        response = client.post(BASE_URL, json=make_profile_payload_dict())

        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link
        assert "/schemas/Profile.json" in link

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

        response = client.post(BASE_URL, json=make_profile_payload_dict())

        assert response.status_code == 409
        assert response.json()["title"] == "Profile already exists"

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

        response = client.post(BASE_URL, json=make_profile_payload_dict())

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
        response = client.post(BASE_URL, json=make_profile_payload_dict())

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

        response = client.post(BASE_URL, json=payload)

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
        payload = make_profile_payload_dict(omit=["first_name"])

        response = client.post(BASE_URL, json=payload)

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "missing_field",
        ["first_name", "last_name", "email", "phone_number", "terms"],
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

        response = client.post(BASE_URL, json=payload)

        assert response.status_code == 422
        body = response.json()
        assert any(missing_field in str(err.get("location", "")) for err in body["errors"])

    def test_returns_422_when_terms_false(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify terms=False returns 422 validation error.
        """
        payload = make_profile_payload_dict(terms=False)

        response = client.post(BASE_URL, json=payload)

        assert response.status_code == 422
        body = response.json()
        assert any("terms" in str(err.get("location", "")) for err in body["errors"])
        assert any("terms must be accepted" in str(err.get("message", "")) for err in body["errors"])


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

        response = client.get(BASE_URL)

        assert response.status_code == 200
        body = response.json()
        assert "id" in body
        assert "first_name" in body
        mock_profile_service.get_profile.assert_awaited_once()

    def test_response_does_not_embed_schema_metadata(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify GET /profile/ keeps schema metadata out of the representation.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(BASE_URL)

        body = response.json()
        assert "$schema" not in body

    def test_returns_describedby_link_header(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify GET /profile/ returns Link header with describedBy.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(BASE_URL)

        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link
        assert "/schemas/Profile.json" in link

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

        response = client.get(BASE_URL)

        assert response.status_code == 404
        assert response.json()["title"] == "Profile not found"

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

        response = client.get(BASE_URL)

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
        response = client.get(BASE_URL)

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
        mock_profile_service.update_profile.return_value = make_profile(first_name="Updated")

        response = client.patch(BASE_URL, json={"first_name": "Updated"})

        assert response.status_code == 200
        body = response.json()
        assert body["first_name"] == "Updated"
        mock_profile_service.update_profile.assert_awaited_once()

    def test_response_does_not_embed_schema_metadata(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify PATCH /profile/ keeps schema metadata out of the representation.
        """
        mock_profile_service.update_profile.return_value = make_profile(first_name="Updated")

        response = client.patch(BASE_URL, json={"first_name": "Updated"})

        body = response.json()
        assert "$schema" not in body

    def test_returns_describedby_link_header(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify PATCH /profile/ returns Link header with describedBy.
        """
        mock_profile_service.update_profile.return_value = make_profile(first_name="Updated")

        response = client.patch(BASE_URL, json={"first_name": "Updated"})

        link = response.headers.get("link", "")
        assert 'rel="describedBy"' in link
        assert "/schemas/Profile.json" in link

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

        response = client.patch(BASE_URL, json={"first_name": "Updated"})

        assert response.status_code == 404
        assert response.json()["title"] == "Profile not found"

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

        response = client.patch(BASE_URL, json={"first_name": "Updated"})

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
        response = client.patch(BASE_URL, json={"first_name": "Updated"})

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
        mock_profile_service.update_profile.return_value = make_profile(last_name="NewLast")

        response = client.patch(BASE_URL, json={"last_name": "NewLast"})

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

        response = client.patch(BASE_URL, json={})

        assert response.status_code == 200

    @pytest.mark.parametrize("field", ["first_name", "last_name", "email", "phone_number", "marketing"])
    def test_rejects_explicit_null(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
        field: str,
    ) -> None:
        """
        Verify explicit null fields return validation errors instead of no-op updates.
        """
        response = client.patch(BASE_URL, json={field: None})

        assert response.status_code == 422
        assert response.json()["detail"] == "validation failed"
        mock_profile_service.update_profile.assert_not_awaited()

    @pytest.mark.parametrize("field", ["firstName", "lastName", "phoneNumber", "firstname", "lastname"])
    def test_rejects_alternate_field_casing(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
        field: str,
    ) -> None:
        """
        Verify PATCH accepts only the documented snake_case property names.
        """
        response = client.patch(BASE_URL, json={field: "value"})

        assert response.status_code == 422
        assert response.json()["detail"] == "validation failed"
        mock_profile_service.update_profile.assert_not_awaited()


class TestDeleteProfile:
    """
    Tests for DELETE /profile/.
    """

    def test_returns_204_on_success(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify successful profile deletion returns 204 No Content.
        """
        mock_profile_service.delete_profile.return_value = None

        response = client.delete(BASE_URL)

        assert response.status_code == 204
        assert response.content == b""
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

        response = client.delete(BASE_URL)

        assert response.status_code == 404
        assert response.json()["title"] == "Profile not found"

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

        response = client.delete(BASE_URL)

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
        response = client.delete(BASE_URL)

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
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        mock_profile_service.get_profile.return_value = profile

        response = client.get(BASE_URL)

        body = response.json()
        assert set(body) == PROFILE_FIELD_NAMES
        assert body["first_name"] == "John"
        assert body["last_name"] == "Doe"
        assert body["email"] == "john@example.com"

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

        response = client.get(BASE_URL)

        body = response.json()
        assert "created_at" in body
        assert "updated_at" in body
