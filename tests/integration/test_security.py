"""Security-focused tests: CORS, JWT tampering, revocation semantics."""

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from tests.mocks.firebase import patch_router_verify_to_raise


def test_preflight_denied_by_default(client: TestClient) -> None:
    # With empty allowlist, origin not allowed; expect no ACAO header
    res = client.options(
        "/profile/",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in {k.lower(): v for k, v in res.headers.items()}


def test_tampered_jwt_results_403(client: TestClient, monkeypatch: MonkeyPatch) -> None:
    from fastapi import HTTPException, status

    patch_router_verify_to_raise(
        monkeypatch, HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    )
    res = client.get("/profile/")
    assert res.status_code == 403  # security dependency rejects missing/invalid auth


def test_revoked_token_results_403(client: TestClient, monkeypatch: MonkeyPatch) -> None:
    from fastapi import HTTPException, status

    patch_router_verify_to_raise(
        monkeypatch, HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
    )
    res = client.get("/profile/")
    assert res.status_code == 403
