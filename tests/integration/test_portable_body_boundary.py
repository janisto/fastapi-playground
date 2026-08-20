"""Chunked ASGI tests for exact inbound limits and body-read ordering."""

import json
from collections.abc import Iterable

import pytest
from starlette.types import Message, Scope


def _scope(
    method: str,
    path: str,
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Scope:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "root_path": "",
        "headers": headers or [],
        "client": ("203.0.113.10", 50000),
        "server": ("testserver", 80),
        "state": {},
    }


async def _request(scope: Scope, chunks: Iterable[bytes]) -> tuple[int, dict[str, str], bytes, int]:
    from app.main import app

    pending = list(chunks)
    receive_calls = 0
    sent: list[Message] = []

    async def receive() -> Message:
        nonlocal receive_calls
        receive_calls += 1
        if not pending:
            raise AssertionError("application read beyond the supplied request content")
        body = pending.pop(0)
        return {"type": "http.request", "body": body, "more_body": bool(pending)}

    async def send(message: Message) -> None:
        sent.append(message)

    await app(scope, receive, send)
    start = next(message for message in sent if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
    headers = {key.decode("latin1"): value.decode("latin1") for key, value in start["headers"]}
    return start["status"], headers, body, receive_calls


@pytest.mark.parametrize("size", [999_999, 1_000_000])
async def test_streamed_body_accepts_exact_boundary(size: int) -> None:
    prefix = b'{"name":"Ada"}'
    payload = prefix + b" " * (size - len(prefix))
    status, _, body, calls = await _request(
        _scope("POST", "/v1/hello", headers=[(b"content-type", b"application/json")]),
        [payload[:400_000], payload[400_000:800_000], payload[800_000:]],
    )
    assert status == 200
    assert json.loads(body) == {"message": "Hello, Ada!"}
    assert calls == 3


async def test_streamed_body_stops_on_first_over_limit_chunk() -> None:
    chunks = [b'{"name":"Ada"}' + b" " * 599_986, b" " * 400_001, b"never-read"]
    status, headers, body, calls = await _request(
        _scope(
            "POST",
            "/v1/hello",
            headers=[(b"content-type", b"application/json"), (b"x-request-id", b"stream-limit")],
        ),
        chunks,
    )
    assert status == 413
    assert json.loads(body)["code"] == "payload_too_large"
    assert headers["x-request-id"] == "stream-limit"
    assert calls == 2


async def test_streamed_profile_body_is_not_read_before_authentication() -> None:
    status, headers, body, calls = await _request(
        _scope("POST", "/v1/profile", headers=[(b"content-type", b"application/json")]),
        [b"x" * 600_000, b"x" * 400_001],
    )
    assert status == 401
    assert json.loads(body)["code"] == "unauthorized"
    assert headers["www-authenticate"] == "Bearer"
    assert calls == 0


@pytest.mark.parametrize(
    ("method", "path", "expected_status"),
    [
        ("GET", "/health", 200),
        ("GET", "/v1/hello", 200),
        ("GET", "/v1/items", 200),
        ("GET", "/openapi.json", 200),
        ("GET", "/v1/profile", 401),
        ("DELETE", "/v1/profile", 401),
        ("GET", "/v1/github/owners/-bad", 422),
        ("PUT", "/v1/hello", 405),
        ("POST", "/missing", 404),
    ],
)
async def test_body_free_unsupported_and_unmatched_requests_do_not_read_content(
    method: str,
    path: str,
    expected_status: int,
) -> None:
    scope = _scope(method, path, headers=[(b"content-length", b"1000001")])
    status, _, _, calls = await _request(scope, [b"must-not-be-read"])
    assert status == expected_status
    assert calls == 0


async def test_declared_over_limit_and_conflicting_length_do_not_read_content() -> None:
    over = _scope(
        "POST",
        "/v1/hello",
        headers=[(b"content-type", b"application/json"), (b"content-length", b"1000001")],
    )
    status, _, body, calls = await _request(over, [b"must-not-be-read"])
    assert status == 413
    assert json.loads(body)["code"] == "payload_too_large"
    assert calls == 0

    conflicting = _scope(
        "POST",
        "/v1/hello",
        headers=[
            (b"content-type", b"application/json"),
            (b"content-length", b"1"),
            (b"content-length", b"2"),
        ],
    )
    status, _, body, calls = await _request(conflicting, [b"must-not-be-read"])
    assert status == 400
    assert json.loads(body)["code"] == "invalid_request"
    assert calls == 0


async def test_declared_length_accepts_decimal_leading_zeroes_and_rejects_overflow() -> None:
    payload = b'{"name":"Ada"}'
    accepted = _scope(
        "POST",
        "/v1/hello",
        headers=[
            (b"content-type", b"application/json"),
            (b"content-length", b"000014"),
            (b"content-length", b"14"),
        ],
    )
    status, _, body, calls = await _request(accepted, [payload])
    assert status == 200
    assert json.loads(body) == {"message": "Hello, Ada!"}
    assert calls == 1

    overflow = _scope(
        "POST",
        "/v1/hello",
        headers=[(b"content-type", b"application/json"), (b"content-length", b"9" * 1000)],
    )
    status, _, body, calls = await _request(overflow, [b"must-not-be-read"])
    assert status == 400
    assert json.loads(body)["code"] == "invalid_request"
    assert calls == 0
