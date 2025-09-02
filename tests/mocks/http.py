"""HTTP client mocking helpers using pytest-httpx."""

from typing import Protocol


class HTTPXMock(Protocol):  # minimal protocol for pytest-httpx fixture
    def add_response(self, *, method: str, url: str, json: dict | None = None, status_code: int = 200) -> None: ...


def add_ok_response(httpx_mock: HTTPXMock, url: str, json: dict | None = None, status_code: int = 200) -> None:
    httpx_mock.add_response(method="GET", url=url, json=json or {"ok": True}, status_code=status_code)


def add_post_response(httpx_mock: HTTPXMock, url: str, json: dict | None = None, status_code: int = 200) -> None:
    httpx_mock.add_response(method="POST", url=url, json=json or {"ok": True}, status_code=status_code)
