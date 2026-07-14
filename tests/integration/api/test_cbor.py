"""
Integration tests for CBOR content negotiation.
"""

from unittest.mock import AsyncMock

import cbor2
import pytest
from fastapi.testclient import TestClient

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


class TestCBORRequest:
    """Tests for CBOR request handling."""

    def test_cbor_request_body_accepted(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify CBOR request body is correctly decoded and processed.
        """
        mock_profile_service.create_profile.return_value = make_profile()
        payload = make_profile_payload_dict()
        cbor_body = cbor2.dumps(payload)

        response = client.post(
            BASE_URL,
            content=cbor_body,
            headers={"Content-Type": "application/cbor"},
        )

        assert response.status_code == 201
        mock_profile_service.create_profile.assert_awaited_once()

    def test_cbor_request_with_cbor_response(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify CBOR request and response works end-to-end.
        """
        profile = make_profile()
        mock_profile_service.create_profile.return_value = profile
        payload = make_profile_payload_dict()
        cbor_body = cbor2.dumps(payload)

        response = client.post(
            BASE_URL,
            content=cbor_body,
            headers={
                "Content-Type": "application/cbor",
                "Accept": "application/cbor",
            },
        )

        assert response.status_code == 201
        assert response.headers["content-type"] == "application/cbor"
        decoded = cbor2.loads(response.content)
        assert set(decoded) == PROFILE_FIELD_NAMES
        assert decoded["first_name"] == profile.first_name
        assert decoded["id"] == profile.id

    def test_unsupported_content_type_returns_415(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unsupported Content-Type returns 415 Unsupported Media Type.
        """
        response = client.post(
            BASE_URL,
            content=b"some data",
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 415
        body = response.json()
        assert body["title"] == "Unsupported Media Type"

    def test_invalid_cbor_returns_400(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify invalid CBOR data returns 400 Bad Request.
        """
        response = client.post(
            BASE_URL,
            content=b"\xff\xff\xff",
            headers={"Content-Type": "application/cbor"},
        )

        assert response.status_code == 400
        body = response.json()
        assert body["title"] == "Invalid CBOR"


class TestCBORResponse:
    """Tests for CBOR response negotiation."""

    def test_accept_cbor_returns_cbor(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify Accept: application/cbor returns CBOR response.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(
            BASE_URL,
            headers={"Accept": "application/cbor"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/cbor"
        decoded = cbor2.loads(response.content)
        assert set(decoded) == PROFILE_FIELD_NAMES

    def test_accept_json_returns_json(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify Accept: application/json returns JSON response.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(
            BASE_URL,
            headers={"Accept": "application/json"},
        )

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        body = response.json()
        assert set(body) == PROFILE_FIELD_NAMES

    def test_default_returns_json(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify no Accept header defaults to JSON response.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(BASE_URL)

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    def test_repeated_accept_fields_are_combined(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify repeated list-based Accept fields participate in one selection.
        """
        mock_profile_service.get_profile.return_value = make_profile()

        response = client.get(
            BASE_URL,
            headers=[
                ("Accept", "application/json;q=0.1"),
                ("Accept", "application/cbor;q=1"),
            ],
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/cbor"

    def test_delete_with_accept_cbor_returns_empty_body(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify DELETE with Accept: application/cbor returns empty body (204).

        Tests the branch where response body is empty during CBOR conversion.
        """
        mock_profile_service.delete_profile.return_value = None

        response = client.delete(
            BASE_URL,
            headers={"Accept": "application/cbor"},
        )

        assert response.status_code == 204
        assert response.content == b""

    @pytest.mark.parametrize(
        ("accept", "content_type"),
        [
            ("application/problem+json", "application/problem+json"),
            ("application/problem+cbor", "application/problem+json"),
        ],
    )
    def test_problem_only_accept_rejects_success_representation(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
        accept: str,
        content_type: str,
    ) -> None:
        """
        Verify Problem Details media types are rejected before endpoint execution.
        """
        response = client.get(BASE_URL, headers={"Accept": accept})

        assert response.status_code == 406
        assert response.headers["content-type"] == content_type
        assert response.json()["title"] == "Not Acceptable"
        mock_profile_service.get_profile.assert_not_awaited()

    @pytest.mark.parametrize(
        ("method", "accept", "service_method"),
        [
            ("post", "application/problem+json", "create_profile"),
            ("patch", "application/problem+cbor", "update_profile"),
        ],
    )
    def test_problem_only_accept_cannot_mutate_profile(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
        method: str,
        accept: str,
        service_method: str,
    ) -> None:
        """
        Verify unsupported success negotiation cannot execute a mutation.
        """
        payloads = {
            "post": make_profile_payload_dict(),
            "patch": {"first_name": "Updated"},
        }

        response = client.request(method, BASE_URL, json=payloads.get(method), headers={"Accept": accept})

        assert response.status_code == 406
        getattr(mock_profile_service, service_method).assert_not_awaited()

    def test_unacceptable_success_precedes_request_body_parsing(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify success negotiation rejects a mutation before JSON parsing.
        """
        response = client.post(
            BASE_URL,
            content=b"not-json",
            headers={"Accept": "application/xml", "Content-Type": "application/json"},
        )

        assert response.status_code == 406
        assert response.headers["content-type"] == "application/problem+json"
        mock_profile_service.create_profile.assert_not_awaited()

    def test_no_content_success_ignores_accept(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify Accept does not gate a 204 response with no representation.
        """
        response = client.delete(BASE_URL, headers={"Accept": "application/xml"})

        assert response.status_code == 204
        assert response.content == b""
        mock_profile_service.delete_profile.assert_awaited_once()


class TestCBORErrorResponse:
    """Tests for CBOR error response negotiation."""

    def test_error_returns_cbor_when_accept_cbor(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify error responses honor Accept: application/cbor.
        """
        from app.exceptions import ProfileNotFoundError

        mock_profile_service.get_profile.side_effect = ProfileNotFoundError()

        response = client.get(
            BASE_URL,
            headers={"Accept": "application/cbor"},
        )

        assert response.status_code == 404
        assert response.headers["content-type"] == "application/cbor"
        decoded = cbor2.loads(response.content)
        assert decoded["title"] == "Profile not found"
        assert decoded["status"] == 404

    def test_validation_error_returns_cbor_when_accept_cbor(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify validation errors return CBOR when Accept header requests it.

        Per RFC 9457, validation errors use 'Unprocessable Entity' title.
        """
        payload = {"email": "not-an-email"}
        cbor_body = cbor2.dumps(payload)

        response = client.post(
            BASE_URL,
            content=cbor_body,
            headers={
                "Content-Type": "application/cbor",
                "Accept": "application/cbor",
            },
        )

        assert response.status_code == 422
        assert response.headers["content-type"] == "application/cbor"
        decoded = cbor2.loads(response.content)
        assert decoded["title"] == "Unprocessable Entity"
        assert decoded["detail"] == "validation failed"
        assert "errors" in decoded
        assert "$schema" not in decoded
