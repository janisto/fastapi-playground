"""
Integration tests for CBOR content negotiation.
"""

from unittest.mock import AsyncMock

import cbor2
from fastapi.testclient import TestClient

from tests.helpers.profiles import make_profile, make_profile_payload_dict

BASE_URL = "/v1/profile"


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
        assert decoded["firstname"] == profile.firstname
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
        assert "id" in decoded
        assert "firstname" in decoded

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
        assert "id" in body
        assert "firstname" in body

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
        assert response.headers["content-type"] == "application/problem+cbor"
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
        assert response.headers["content-type"] == "application/problem+cbor"
        decoded = cbor2.loads(response.content)
        assert decoded["title"] == "Unprocessable Entity"
        assert decoded["detail"] == "validation failed"
        assert "errors" in decoded
        assert "$schema" in decoded
