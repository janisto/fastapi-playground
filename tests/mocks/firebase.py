"""
Firebase-related mocks used across tests.
"""

from unittest.mock import MagicMock

from pytest import MonkeyPatch


def mock_verify_id_token_ok(
    uid: str = "test-user-123",
    email: str = "test@example.com",
) -> dict[str, object]:
    """
    Return a fake decoded token payload.
    """
    return {"uid": uid, "email": email, "email_verified": True}


def patch_firebase_verify_ok(
    monkeypatch: MonkeyPatch,
    uid: str = "test-user-123",
    email: str = "test@example.com",
) -> None:
    """
    Patch firebase_admin.auth.verify_id_token to return a valid payload.
    """
    import app.auth.firebase as auth_mod

    def _fake_verify(token: str, app: object = None, *, check_revoked: bool = False) -> dict[str, object]:
        return mock_verify_id_token_ok(uid=uid, email=email)

    monkeypatch.setattr(auth_mod.auth, "verify_id_token", _fake_verify)


def patch_firebase_verify_error(monkeypatch: MonkeyPatch, error: Exception) -> None:
    """
    Patch firebase_admin.auth.verify_id_token to raise the specified error.
    """
    import app.auth.firebase as auth_mod

    def _raise(*args: object, **kwargs: object) -> None:
        raise error

    monkeypatch.setattr(auth_mod.auth, "verify_id_token", _raise)


def patch_get_firebase_app(monkeypatch: MonkeyPatch) -> None:
    """
    Patch get_firebase_app to return a MagicMock app instance.
    """
    import app.auth.firebase as auth_mod

    monkeypatch.setattr(auth_mod, "get_firebase_app", MagicMock)


def patch_router_verify_to_raise(monkeypatch: MonkeyPatch, exc: Exception) -> None:
    """
    Patch verify_firebase_token to raise the provided exception.

    Useful in integration tests to simulate invalid/revoked tokens quickly.
    """
    import app.auth.firebase as firebase_auth

    def _raise(*args: object, **kwargs: object) -> None:
        raise exc

    monkeypatch.setattr(firebase_auth, "verify_firebase_token", _raise)
