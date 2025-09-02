"""Firebase-related mocks used across tests."""

from unittest.mock import MagicMock

from pytest import MonkeyPatch


def mock_verify_id_token_ok(uid: str = "test-user-123", email: str = "test@example.com") -> dict[str, object]:
    return {"uid": uid, "email": email, "email_verified": True}


def patch_firebase_verify_ok(monkeypatch: MonkeyPatch) -> None:
    """Patch firebase_admin.auth.verify_id_token to return a valid payload."""
    import app.auth.firebase as auth_mod

    def _fake_verify(token: str, app=None) -> dict[str, object]:  # noqa: ANN001 - external API compatibility
        return mock_verify_id_token_ok()

    monkeypatch.setattr(auth_mod.auth, "verify_id_token", _fake_verify)


def patch_get_firebase_app(monkeypatch: MonkeyPatch) -> None:
    """Patch get_firebase_app to return a MagicMock app instance."""
    import app.auth.firebase as auth_mod

    monkeypatch.setattr(auth_mod, "get_firebase_app", lambda: MagicMock())


def patch_router_verify_to_raise(monkeypatch: MonkeyPatch, exc: Exception) -> None:
    """Patch app.routers.profile.verify_firebase_token to raise the provided exception.

    Useful in integration tests to simulate invalid/revoked tokens quickly.
    """
    import app.routers.profile as profile_router

    def _raise(*args: object, **kwargs: object) -> None:  # noqa: ANN001, ANN002 - test helper shim
        raise exc

    monkeypatch.setattr(profile_router, "verify_firebase_token", _raise)
