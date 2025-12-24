"""
Unit tests for Firebase authentication.
"""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from firebase_admin.auth import (
    CertificateFetchError,
    ExpiredIdTokenError,
    InvalidIdTokenError,
    RevokedIdTokenError,
    UserDisabledError,
)
from pytest import MonkeyPatch

from app.auth.firebase import FirebaseUser, verify_firebase_token
from tests.mocks.firebase import (
    patch_firebase_verify_error,
    patch_firebase_verify_ok,
    patch_get_firebase_app,
)


def _make_credentials(token: str = "test-token") -> HTTPAuthorizationCredentials:
    """
    Create mock HTTPAuthorizationCredentials for testing.
    """
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


class TestFirebaseUser:
    """
    Tests for FirebaseUser dataclass.
    """

    def test_create_with_all_fields(self) -> None:
        """
        Verify FirebaseUser creation with all fields.
        """
        user = FirebaseUser(uid="user-123", email="user@example.com", email_verified=True)
        assert user.uid == "user-123"
        assert user.email == "user@example.com"
        assert user.email_verified is True

    def test_create_with_defaults(self) -> None:
        """
        Verify FirebaseUser creation with default values.
        """
        user = FirebaseUser(uid="user-123")
        assert user.uid == "user-123"
        assert user.email is None
        assert user.email_verified is False

    def test_is_frozen(self) -> None:
        """
        Verify FirebaseUser is immutable.
        """
        user = FirebaseUser(uid="user-123")
        with pytest.raises(AttributeError):
            user.uid = "modified"  # type: ignore[misc]


class TestVerifyFirebaseToken:
    """
    Tests for verify_firebase_token dependency.
    """

    async def test_valid_token_returns_user(self, monkeypatch: MonkeyPatch) -> None:
        """
        Verify valid token returns FirebaseUser.
        """
        patch_get_firebase_app(monkeypatch)
        patch_firebase_verify_ok(monkeypatch, uid="user-123", email="user@example.com")

        credentials = _make_credentials("valid-token")
        user = await verify_firebase_token(credentials)

        assert isinstance(user, FirebaseUser)
        assert user.uid == "user-123"
        assert user.email == "user@example.com"
        assert user.email_verified is True

    async def test_expired_token_raises_401(self, monkeypatch: MonkeyPatch) -> None:
        """
        Verify expired token raises HTTPException with 401.
        """
        patch_get_firebase_app(monkeypatch)
        patch_firebase_verify_error(monkeypatch, ExpiredIdTokenError("Token expired", None))

        credentials = _make_credentials("expired-token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    async def test_revoked_token_raises_401(self, monkeypatch: MonkeyPatch) -> None:
        """
        Verify revoked token raises HTTPException with 401.
        """
        patch_get_firebase_app(monkeypatch)
        patch_firebase_verify_error(monkeypatch, RevokedIdTokenError("Token revoked"))

        credentials = _make_credentials("revoked-token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"

    async def test_invalid_token_raises_401(self, monkeypatch: MonkeyPatch) -> None:
        """
        Verify invalid token raises HTTPException with 401.
        """
        patch_get_firebase_app(monkeypatch)
        patch_firebase_verify_error(monkeypatch, InvalidIdTokenError("Invalid token"))

        credentials = _make_credentials("invalid-token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"

    async def test_disabled_user_raises_401(self, monkeypatch: MonkeyPatch) -> None:
        """
        Verify disabled user raises HTTPException with 401.
        """
        patch_get_firebase_app(monkeypatch)
        patch_firebase_verify_error(monkeypatch, UserDisabledError("User disabled"))

        credentials = _make_credentials("disabled-user-token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"

    async def test_generic_error_raises_401(self, monkeypatch: MonkeyPatch) -> None:
        """
        Verify generic errors raise HTTPException with 401.
        """
        patch_get_firebase_app(monkeypatch)
        patch_firebase_verify_error(monkeypatch, RuntimeError("Unexpected error"))

        credentials = _make_credentials("error-token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Unauthorized"

    async def test_certificate_fetch_error_raises_503(self, monkeypatch: MonkeyPatch) -> None:
        """
        Verify CertificateFetchError raises HTTPException with 503.

        This occurs when Firebase SDK cannot fetch public keys for token verification
        due to network issues or configuration problems.
        """
        patch_get_firebase_app(monkeypatch)
        patch_firebase_verify_error(
            monkeypatch,
            CertificateFetchError("Failed to fetch certificates", cause=None),
        )

        credentials = _make_credentials("valid-token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == "Authentication service temporarily unavailable"
        assert exc_info.value.headers == {"Retry-After": "30"}

    async def test_missing_uid_raises_401(self, monkeypatch: MonkeyPatch) -> None:
        """
        Verify token without uid raises HTTPException with 401.
        """
        patch_get_firebase_app(monkeypatch)

        import app.auth.firebase as auth_mod

        def _fake_verify(token: str, app: object = None, check_revoked: bool = False) -> dict:
            return {"email": "user@example.com"}

        monkeypatch.setattr(auth_mod.auth, "verify_id_token", _fake_verify)

        credentials = _make_credentials("no-uid-token")

        with pytest.raises(HTTPException) as exc_info:
            await verify_firebase_token(credentials)

        assert exc_info.value.status_code == 401

    async def test_email_not_verified(self, monkeypatch: MonkeyPatch) -> None:
        """
        Verify user with unverified email is returned correctly.
        """
        patch_get_firebase_app(monkeypatch)

        import app.auth.firebase as auth_mod

        def _fake_verify(token: str, app: object = None, check_revoked: bool = False) -> dict:
            return {"uid": "user-123", "email": "user@example.com", "email_verified": False}

        monkeypatch.setattr(auth_mod.auth, "verify_id_token", _fake_verify)

        credentials = _make_credentials("valid-token")
        user = await verify_firebase_token(credentials)

        assert user.uid == "user-123"
        assert user.email_verified is False


class TestVerifyFirebaseTokenLogging:
    """
    Tests for authentication logging behavior.
    """

    async def test_successful_auth_logs_at_debug_level(
        self, monkeypatch: MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Verify successful authentication logs at DEBUG level, not INFO.
        """
        import logging

        patch_get_firebase_app(monkeypatch)
        patch_firebase_verify_ok(monkeypatch, uid="user-123")

        credentials = _make_credentials("valid-token")

        with caplog.at_level(logging.DEBUG):
            await verify_firebase_token(credentials)

        auth_logs = [r for r in caplog.records if "Successfully authenticated" in r.message]
        assert len(auth_logs) == 1
        assert auth_logs[0].levelno == logging.DEBUG

    async def test_missing_uid_logs_at_warning_level(
        self, monkeypatch: MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """
        Verify missing UID logs at WARNING level.
        """
        import logging

        patch_get_firebase_app(monkeypatch)

        import app.auth.firebase as auth_mod

        def _fake_verify(token: str, app: object = None, check_revoked: bool = False) -> dict:
            return {"email": "user@example.com"}

        monkeypatch.setattr(auth_mod.auth, "verify_id_token", _fake_verify)

        credentials = _make_credentials("no-uid-token")

        with caplog.at_level(logging.DEBUG), pytest.raises(HTTPException):
            await verify_firebase_token(credentials)

        warning_logs = [r for r in caplog.records if "missing user ID" in r.message]
        assert len(warning_logs) == 1
        assert warning_logs[0].levelno == logging.WARNING


class TestHTTPBearerSecurity:
    """
    Tests for HTTP Bearer security scheme.
    """

    def test_security_scheme_exists(self) -> None:
        """
        Verify security scheme is defined.
        """
        from app.auth.firebase import security

        assert security is not None
        assert security.scheme_name == "HTTPBearer"
