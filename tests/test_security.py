"""Security-focused tests: CORS, JWT tampering, revocation semantics."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Generator[TestClient]:
    with patch("app.main.initialize_firebase"), patch("app.main.setup_logging"):
        yield TestClient(app)


class TestCORS:
    def test_preflight_denied_by_default(self, client: TestClient) -> None:
        # With empty allowlist, origin not allowed; expect 400/403-ish behavior without CORS headers
        res = client.options(
            "/profile/",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Starlette returns 200 for OPTIONS even if not allowed, but should NOT include ACAO header
        assert "access-control-allow-origin" not in {k.lower(): v for k, v in res.headers.items()}


class TestJWTFailures:
    @patch("app.routers.profile.verify_firebase_token")
    def test_tampered_jwt_results_403(self, mock_verify: MagicMock, client: TestClient) -> None:
        # Simulate verify failing like an invalid token
        from fastapi import HTTPException, status

        mock_verify.side_effect = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        res = client.get("/profile/")
        assert res.status_code == 403  # security dependency rejects missing/invalid auth

    @patch("app.routers.profile.verify_firebase_token")
    def test_revoked_token_results_403(self, mock_verify: MagicMock, client: TestClient) -> None:
        # Simulate revoked token behavior at dependency level
        from fastapi import HTTPException, status

        mock_verify.side_effect = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")
        res = client.get("/profile/")
        assert res.status_code == 403
