"""
Integration tests for error response schema discovery.

RFC 9457 response instances contain problem details only. Their JSON Schema is
advertised separately through a Link header with the describedBy relation.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.constants import PROBLEM_SCHEMA_PATH, VALIDATION_PROBLEM_SCHEMA_PATH
from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from tests.helpers.profiles import make_profile_payload_dict

BASE_URL = "/v1/profile"


def assert_schema_link(response_body: dict[str, object], link: str, expected_path: str) -> None:
    """
    Assert that schema discovery uses a portable Link header only.
    """
    assert "$schema" not in response_body
    assert f"<{expected_path}>" in link
    assert 'rel="describedBy"' in link


class TestErrorSchemaDiscovery:
    """
    Tests for schema discovery on error responses.
    """

    @pytest.mark.parametrize("method", ["get", "post"])
    def test_401_uses_problem_schema(self, client: TestClient, method: str) -> None:
        """
        Verify authentication failures advertise the generic problem schema.
        """
        response = getattr(client, method)(BASE_URL)

        assert response.status_code == 401
        assert_schema_link(response.json(), response.headers["link"], PROBLEM_SCHEMA_PATH)

    def test_404_uses_problem_schema(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify not-found failures advertise the generic problem schema.
        """
        mock_profile_service.get_profile.side_effect = ProfileNotFoundError()

        response = client.get(BASE_URL)

        assert response.status_code == 404
        assert_schema_link(response.json(), response.headers["link"], PROBLEM_SCHEMA_PATH)

    def test_409_uses_problem_schema(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify conflict failures advertise the generic problem schema.
        """
        mock_profile_service.create_profile.side_effect = ProfileAlreadyExistsError()

        response = client.post(BASE_URL, json=make_profile_payload_dict())

        assert response.status_code == 409
        assert_schema_link(response.json(), response.headers["link"], PROBLEM_SCHEMA_PATH)

    def test_422_uses_validation_schema(self, client: TestClient, with_fake_user: None) -> None:
        """
        Verify validation failures advertise the validation problem schema.
        """
        response = client.post(BASE_URL, json={"invalid": "data"})

        assert response.status_code == 422
        assert_schema_link(response.json(), response.headers["link"], VALIDATION_PROBLEM_SCHEMA_PATH)

    def test_500_uses_problem_schema(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unexpected failures advertise the generic problem schema.
        """
        mock_profile_service.get_profile.side_effect = RuntimeError("Database failure")

        response = client.get(BASE_URL)

        assert response.status_code == 500
        assert_schema_link(response.json(), response.headers["link"], PROBLEM_SCHEMA_PATH)
