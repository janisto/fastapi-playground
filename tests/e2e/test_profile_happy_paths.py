"""E2E-style happy path flows for profile endpoints (with external services mocked)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from tests.helpers.profiles import make_profile, make_profile_payload_dict


def test_create_profile_success(client: TestClient, with_fake_user: None) -> None:
    with (
        patch("app.services.profile.profile_service.get_profile") as mock_get,
        patch("app.services.profile.profile_service.create_profile") as mock_create,
    ):
        mock_get.return_value = None
        mock_create.return_value = make_profile()

        payload = make_profile_payload_dict()
        res = client.post("/profile/", json=payload)
        assert res.status_code == 201
        body = res.json()
        assert body["success"] is True
        assert body["profile"]["firstname"] == "John"


def test_get_profile_success(client: TestClient, with_fake_user: None) -> None:
    with patch("app.services.profile.profile_service.get_profile") as mock_get:
        mock_get.return_value = make_profile()

        res = client.get("/profile/")
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["profile"]["email"] == "john@example.com"
