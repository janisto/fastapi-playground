"""
HTTP client mocking helpers using pytest-httpx.
"""

from typing import Protocol


class HTTPXMock(Protocol):
    """
    Minimal protocol for pytest-httpx fixture type hints.
    """

    def add_response(
        self,
        *,
        method: str,
        url: str,
        json: dict | None = None,
        status_code: int = 200,
    ) -> None: ...

    def add_exception(self, exception: Exception) -> None: ...


def add_ok_response(
    httpx_mock: HTTPXMock,
    url: str,
    json: dict | None = None,
    status_code: int = 200,
) -> None:
    """
    Add a successful GET response to the mock.
    """
    httpx_mock.add_response(
        method="GET",
        url=url,
        json=json or {"ok": True},
        status_code=status_code,
    )


def add_post_response(
    httpx_mock: HTTPXMock,
    url: str,
    json: dict | None = None,
    status_code: int = 200,
) -> None:
    """
    Add a successful POST response to the mock.
    """
    httpx_mock.add_response(
        method="POST",
        url=url,
        json=json or {"ok": True},
        status_code=status_code,
    )


def add_error_response(
    httpx_mock: HTTPXMock,
    url: str,
    status_code: int = 500,
    method: str = "GET",
    json: dict | None = None,
) -> None:
    """
    Add an error response to the mock.
    """
    httpx_mock.add_response(
        method=method,
        url=url,
        json=json or {"error": "Internal Server Error"},
        status_code=status_code,
    )
