import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from app.core.body_limit import BodySizeLimitMiddleware
from app.core.config import get_settings


def _app() -> Starlette:
    app = Starlette()

    @app.route("/echo", methods=["POST"])
    async def echo(request: Request) -> Response:  # type: ignore[override]
        data = await request.body()
        return Response(data, media_type="application/octet-stream")

    app.add_middleware(BodySizeLimitMiddleware)
    return app


def test_reject_via_content_length(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_REQUEST_SIZE_BYTES", "10")
    # Reset cached settings so middleware sees updated env var
    get_settings.cache_clear()  # type: ignore[attr-defined]
    with TestClient(_app()) as client:
        resp = client.post("/echo", data=b"x" * 11, headers={"Content-Length": "11"})
        assert resp.status_code == 413
        assert resp.json()["detail"].startswith("Request body too large")


def test_reject_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_REQUEST_SIZE_BYTES", "5")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    with TestClient(_app()) as client:
        resp = client.post("/echo", data=b"abcdef")
        assert resp.status_code == 413


def test_accept_under_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_REQUEST_SIZE_BYTES", "100")
    get_settings.cache_clear()  # type: ignore[attr-defined]
    with TestClient(_app()) as client:
        payload = b"hello"
        resp = client.post("/echo", data=payload)
        assert resp.status_code == 200
        assert resp.content == payload
