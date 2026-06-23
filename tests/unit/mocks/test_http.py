"""
Tests for httpx2 mock helpers.
"""

import httpx2
import pytest
from respx import Router

from tests.mocks.http import add_error_response, add_ok_response, add_post_response


class TestHTTPX2MockHelpers:
    """
    Tests for pytest-httpx2 helper functions.
    """

    def test_add_ok_response_mocks_get_request(self, httpx2_mock: Router) -> None:
        """
        Verify add_ok_response registers a GET response on the httpx2 mock.
        """
        route = add_ok_response(httpx2_mock, "https://api.example.test/status")

        response = httpx2.get("https://api.example.test/status")

        assert route.called
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_add_post_response_mocks_post_request(self, httpx2_mock: Router) -> None:
        """
        Verify add_post_response registers a POST response on the httpx2 mock.
        """
        route = add_post_response(
            httpx2_mock,
            "https://api.example.test/items",
            json={"id": "item-1"},
            status_code=201,
        )

        response = httpx2.post("https://api.example.test/items", json={"name": "Test"})

        assert route.called
        assert response.status_code == 201
        assert response.json() == {"id": "item-1"}

    def test_add_error_response_mocks_requested_method(self, httpx2_mock: Router) -> None:
        """
        Verify add_error_response registers the requested HTTP method.
        """
        route = add_error_response(
            httpx2_mock,
            "https://api.example.test/items/item-1",
            method="PATCH",
            status_code=503,
            json={"error": "Unavailable"},
        )

        response = httpx2.patch("https://api.example.test/items/item-1", json={"name": "Updated"})

        assert route.called
        assert response.status_code == 503
        assert response.json() == {"error": "Unavailable"}

    def test_httpx2_mock_can_raise_httpx2_exception(self, httpx2_mock: Router) -> None:
        """
        Verify pytest-httpx2 supports httpx2 exception side effects.
        """
        httpx2_mock.get("https://api.example.test/timeout").mock(side_effect=httpx2.ReadTimeout("Timed out"))

        with pytest.raises(httpx2.ReadTimeout):
            httpx2.get("https://api.example.test/timeout")
