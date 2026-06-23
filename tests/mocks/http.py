"""
HTTP client mocking helpers using pytest-httpx2.
"""

from respx import Router
from respx.models import Route


def add_ok_response(
    httpx2_mock: Router,
    url: str,
    json: dict | None = None,
    status_code: int = 200,
) -> Route:
    """
    Add a successful GET response to the mock.
    """
    return httpx2_mock.get(url).respond(status_code=status_code, json=json or {"ok": True})


def add_post_response(
    httpx2_mock: Router,
    url: str,
    json: dict | None = None,
    status_code: int = 200,
) -> Route:
    """
    Add a successful POST response to the mock.
    """
    return httpx2_mock.post(url).respond(status_code=status_code, json=json or {"ok": True})


def add_error_response(
    httpx2_mock: Router,
    url: str,
    status_code: int = 500,
    method: str = "GET",
    json: dict | None = None,
) -> Route:
    """
    Add an error response to the mock.
    """
    route = httpx2_mock.request(method, url)
    return route.respond(status_code=status_code, json=json or {"error": "Internal Server Error"})
