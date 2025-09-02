"""Authentication helpers for tests."""

from collections.abc import Callable, Generator
from contextlib import contextmanager

from app.auth.firebase import FirebaseUser
from app.main import app


def make_fake_user(uid: str = "test-user-123", email: str = "test@example.com", verified: bool = True) -> FirebaseUser:
    """Factory for a fake FirebaseUser."""
    return FirebaseUser(uid=uid, email=email, email_verified=verified)


@contextmanager
def override_current_user(user_factory: Callable[[], FirebaseUser]) -> Generator[None]:
    """Temporarily override the router auth dependency to yield a fake user.

    Usage:
        with override_current_user(lambda: make_fake_user()):
            ... perform client calls ...
    """
    from app.routers.profile import _current_user_dependency

    def _override() -> FirebaseUser:
        # Return a deterministic fake user without requiring Authorization header
        return user_factory()

    app.dependency_overrides[_current_user_dependency] = _override
    try:
        yield
    finally:
        app.dependency_overrides.clear()
