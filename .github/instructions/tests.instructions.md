---
applyTo: "tests/**"
---

Use these rules for tests under `tests/**` (Python 3.14, FastAPI, pytest, pytest-asyncio). The project uses `httpx` for HTTP clients and `pytest-httpx` for mocking outbound HTTP in tests.

> **Ruff Linter Coverage**: Test patterns are enforced via Ruff (see `pyproject.toml`):
> - **PT**: Pytest style (fixture parentheses, assertion patterns, parametrize syntax, marks)
> - **ANN**: Type annotations for fixtures and test functions
> - **UP**: Modern syntax (use `collections.abc.Generator`, not `typing.Generator`)
> - **S101**: Assert allowed in tests via per-file-ignores
> - **RET504**: Unnecessary assignment allowed in tests for clarity
>
> Run `just lint` to check. This document focuses on project-specific test conventions.

Structure
- Unit tests → `tests/unit/**` (mirror `app/**` folder structure)
- Integration/API tests → `tests/integration/**` (mirror `app/routers/**` structure)
- Fixtures → `tests/conftest.py` and scoped `conftest.py` files
- Helpers → `tests/helpers/**` (factory functions, context managers, utilities)
- Mocks → `tests/mocks/**` (reusable stubs, Protocol types, mock configurations)
- E2E tests → `tests/e2e/**` (local only, requires Firebase emulators)

Folder Structure (mirrors `app/`):
```
tests/
├── conftest.py                       # Root fixtures (client, fake_user, with_fake_user)
├── helpers/                          # Test utilities
│   ├── assertions.py                 # Response assertion helpers
│   ├── auth.py                       # Auth fixtures and context managers
│   ├── clients.py                    # TestClient context manager
│   ├── profiles.py                   # Profile factory functions
│   └── starlette_utils.py            # Minimal Starlette app builders
├── mocks/                            # Mock objects
│   ├── firebase.py                   # Firebase auth mocks
│   ├── firestore.py                  # Fake Firestore client/collections
│   ├── http.py                       # HTTP mock helpers
│   └── services.py                   # Service layer mocks
├── unit/                             # Mirrors app/ structure
│   ├── conftest.py                   # Unit-specific fixtures (reset_settings_cache)
│   ├── test_dependencies.py          # ← app/dependencies.py
│   ├── test_main.py                  # ← app/main.py (lifespan, app config)
│   ├── auth/
│   │   └── test_firebase.py          # ← app/auth/firebase.py
│   ├── core/
│   │   ├── test_config.py            # ← app/core/config.py
│   │   ├── test_firebase.py          # ← app/core/firebase.py
│   │   └── handlers/
│   │       ├── test_domain.py        # ← app/core/handlers/domain.py
│   │       ├── test_http.py          # ← app/core/handlers/http.py
│   │       └── test_validation.py    # ← app/core/handlers/validation.py
│   ├── exceptions/
│   │   ├── test_base.py              # ← app/exceptions/base.py
│   │   └── test_profile.py           # ← app/exceptions/profile.py
│   ├── middleware/
│   │   ├── test_body_limit.py        # ← app/middleware/body_limit.py
│   │   ├── test_logging.py           # ← app/middleware/logging.py
│   │   └── test_security.py          # ← app/middleware/security.py
│   ├── models/
│   │   ├── test_error.py             # ← app/models/error.py
│   │   ├── test_health.py            # ← app/models/health.py
│   │   ├── test_profile_model.py     # ← app/models/profile.py
│   │   └── test_types.py             # ← app/models/types.py
│   └── services/
│       └── test_profile.py           # ← app/services/profile.py
├── integration/                      # Mirrors app/routers/ structure
│   ├── conftest.py                   # Integration fixtures (mock_profile_service, client)
│   └── routers/
│       ├── test_health.py            # ← app/routers/health.py
│       ├── test_root.py              # ← app/main.py (root endpoint)
│       └── test_profile.py           # ← app/routers/profile.py
└── e2e/                              # Real Firebase emulator tests
    ├── conftest.py                   # E2E fixtures (emulator detection, cleanup)
    └── routers/
        └── test_profile.py           # Profile CRUD with real Firestore
```

Unit vs Integration vs E2E: The Simple Rule

> **If your test uses the `client` fixture (real app TestClient), it's an integration test.**
> **If your test uses Firebase emulators, it's an E2E test.**
> **Everything else is a unit test.**

| Criterion | Unit Test | Integration Test | E2E Test |
|-----------|-----------|------------------|----------|
| Uses `client` fixture? | No | Yes | Yes |
| Mocks ProfileService? | N/A | Yes | No |
| Uses real Firestore? | No | No | Yes (emulator) |
| Included in CI? | Yes | Yes | No |
| Requires `just emulators`? | No | No | Yes |

Test File Mapping:

| `app/` module | `tests/unit/` path | `tests/integration/` path |
|---------------|--------------------|-----------------------------|
| `app/main.py` | `tests/unit/test_main.py` | `tests/integration/routers/test_root.py` |
| `app/dependencies.py` | `tests/unit/test_dependencies.py` | - |
| `app/auth/firebase.py` | `tests/unit/auth/test_firebase.py` | - |
| `app/core/config.py` | `tests/unit/core/test_config.py` | - |
| `app/core/firebase.py` | `tests/unit/core/test_firebase.py` | - |
| `app/core/handlers/domain.py` | `tests/unit/core/handlers/test_domain.py` | - |
| `app/core/handlers/http.py` | `tests/unit/core/handlers/test_http.py` | - |
| `app/core/handlers/validation.py` | `tests/unit/core/handlers/test_validation.py` | - |
| `app/exceptions/base.py` | `tests/unit/exceptions/test_base.py` | - |
| `app/exceptions/profile.py` | `tests/unit/exceptions/test_profile.py` | - |
| `app/middleware/body_limit.py` | `tests/unit/middleware/test_body_limit.py` | - |
| `app/middleware/logging.py` | `tests/unit/middleware/test_logging.py` | - |
| `app/middleware/security.py` | `tests/unit/middleware/test_security.py` | - |
| `app/models/error.py` | `tests/unit/models/test_error.py` | - |
| `app/models/health.py` | `tests/unit/models/test_health.py` | - |
| `app/models/profile.py` | `tests/unit/models/test_profile_model.py` | - |
| `app/models/types.py` | `tests/unit/models/test_types.py` | - |
| `app/services/profile.py` | `tests/unit/services/test_profile.py` | - |
| `app/routers/health.py` | - | `tests/integration/routers/test_health.py` |
| `app/routers/profile.py` | - | `tests/integration/routers/test_profile.py` |

Conventions
- No real network, files, or Firebase/Google Cloud in unit/integration tests; mock `firebase_admin` and any external I/O.
- Prefer FastAPI patterns from the docs: use `TestClient` for sync-style API tests; use `httpx.AsyncClient` for true async cases (no `@pytest.mark.asyncio` needed with `asyncio_mode = "auto"`).
- HTTP client and mocking: use `httpx` in code; stub outbound HTTP with `pytest-httpx` via the `httpx_mock` fixture. Do not hit the real network.
- **Prefer `pytest-mock` (`mocker` fixture) over `monkeypatch`** when mocking. Use `mocker.patch()` for patching with `MagicMock`/`AsyncMock` features (call assertions, return values, side effects). Reserve `monkeypatch` for simpler cases: environment variables (`setenv`), `sys.path` manipulation, or `chdir`. Choose the right tool for the task.
- Override dependencies via `app.dependency_overrides` (e.g., auth/user, database/session). Reset overrides after each test to avoid leakage.
- **URL formatting**: Always use paths with a trailing slash (e.g., `"/profile/"` not `"/profile"`). This ensures consistency and avoids 307 redirects.
- Aim ≥90% coverage overall; 100% on critical business logic (auth, security, error handling).
- Validate API contracts: assert status codes, JSON shapes, and headers.
- Use realistic but synthetic fixtures. Never log or include secrets/PII in test data.

Comment discipline
- Do not add progress or narrative comments (e.g., "setting up test", "now calling endpoint").
- Keep comments only for complex fixture setup, intricate mocking, race-condition mitigation, or rationale behind unusual assertions.
- Do not duplicate the test name or obvious Given/When/Then steps in comments.
- Remove outdated comments immediately when altering test logic.

Naming Conventions

Test functions:
```python
# Pattern: test_<what>_<condition/scenario>
def test_health_check_returns_ok() -> None: ...
def test_create_profile_with_invalid_email_returns_422() -> None: ...
```

Test classes - group related tests for a single endpoint or feature:
```python
class TestHealthEndpoint:
    def test_returns_ok(self, client: TestClient) -> None: ...
    def test_database_failure(self, client: TestClient) -> None: ...
```

When to use classes vs standalone functions:
- Use `class TestX` when testing a single endpoint/feature with multiple scenarios
- Use standalone `test_x` functions for isolated, unrelated tests
- Classes help organize tests in editor outlines and test output

BASE_URL pattern - define a module-level constant for endpoint tests:
```python
BASE_URL = "/profile"

class TestGetProfile:
    def test_returns_profile(self, client: TestClient) -> None:
        response = client.get(f"{BASE_URL}/")
        assert response.status_code == 200
```

Fixtures

Fixtures are organized hierarchically - pytest automatically discovers fixtures from parent `conftest.py` files.

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Shared fixtures available to all tests (`client`, `fake_user`, `with_fake_user`) |
| `tests/unit/conftest.py` | Unit-specific fixtures (`reset_settings_cache` autouse) |
| `tests/integration/conftest.py` | Integration fixtures (`mock_profile_service`, `client` with mocked services) |
| `tests/e2e/conftest.py` | E2E fixtures (`require_emulators`, `clear_emulator_data`, `e2e_client`) |

Root conftest fixtures (`tests/conftest.py`):
```python
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.auth.firebase import FirebaseUser
from app.main import app
from tests.helpers.auth import make_fake_user, override_current_user


@pytest.fixture
def client() -> Generator[TestClient]:
    """
    FastAPI TestClient with startup/shutdown and external init patched.
    """
    with (
        patch("app.main.initialize_firebase"),
        patch("app.main.setup_logging"),
        patch("app.main.close_async_firestore_client"),
        TestClient(app) as c,
    ):
        yield c


@pytest.fixture
def fake_user() -> FirebaseUser:
    """
    A simple fake FirebaseUser for auth overrides/tests.
    """
    return make_fake_user()


@pytest.fixture
def with_fake_user(fake_user: FirebaseUser) -> Generator[None]:
    """
    Override router current user for the duration of a test.
    """
    with override_current_user(lambda: fake_user):
        yield
```

Integration conftest fixtures (`tests/integration/conftest.py`):
```python
from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.firebase import FirebaseUser, verify_firebase_token
from app.dependencies import get_profile_service
from app.main import app
from app.services.profile import ProfileService
from tests.helpers.auth import make_fake_user


@pytest.fixture
def mock_profile_service() -> AsyncMock:
    """
    Mocked ProfileService for integration tests.
    """
    return AsyncMock(spec=ProfileService)


@pytest.fixture
def client(mock_profile_service: AsyncMock) -> Generator[TestClient]:
    """
    TestClient with mocked services (no Firebase/Firestore).
    """
    with (
        patch("app.main.initialize_firebase"),
        patch("app.main.setup_logging"),
        patch("app.main.close_async_firestore_client"),
    ):
        app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


@pytest.fixture
def with_fake_user(fake_user: FirebaseUser) -> Generator[None]:
    """
    Override auth to return fake user.
    """
    app.dependency_overrides[verify_firebase_token] = lambda: fake_user
    yield
    app.dependency_overrides.pop(verify_firebase_token, None)
```

Unit conftest fixtures (`tests/unit/conftest.py`):
```python
from collections.abc import Generator

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def reset_settings_cache() -> Generator[None]:
    """
    Reset settings cache before and after each unit test.

    Ensures environment variable changes in tests don't leak.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

E2E conftest fixtures (`tests/e2e/conftest.py`):
```python
import contextlib
import os
from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

FIRESTORE_HOST = "127.0.0.1:7030"
AUTH_HOST = "127.0.0.1:7010"
PROJECT_ID = "demo-test"


def _emulator_running(host: str) -> bool:
    """
    Check if an emulator is running at the given host.
    """
    try:
        httpx.get(f"http://{host}/", timeout=1.0)
        return True
    except httpx.RequestError:
        return False


@pytest.fixture(scope="session", autouse=True)
def require_emulators() -> None:
    """
    Skip all E2E tests if emulators are not running.
    """
    if not _emulator_running(FIRESTORE_HOST):
        pytest.skip("Firebase emulators not running (run: just emulators)")

    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_HOST
    os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = AUTH_HOST


@pytest.fixture(autouse=True)
def clear_emulator_data() -> Generator[None]:
    """
    Clear Firestore emulator data after each test.
    """
    yield
    with contextlib.suppress(httpx.RequestError):
        httpx.delete(
            f"http://{FIRESTORE_HOST}/emulator/v1/projects/{PROJECT_ID}/databases/(default)/documents",
            timeout=5.0,
        )


@pytest.fixture
def e2e_client() -> Generator[TestClient]:
    """
    TestClient for E2E tests against real emulators.

    Unlike integration tests, this does NOT mock Firebase/Firestore.
    """
    with TestClient(app) as c:
        yield c
```

Fixture scope guide:

| Scope | Use Case | Lifetime |
|-------|----------|----------|
| `function` | Default, isolated per test | Created/destroyed per test |
| `class` | Shared across class methods | Created once per test class |
| `module` | Shared across module | Created once per test file |
| `session` | Shared across entire run | Created once, reused everywhere |

When to use each scope:
- `function` (default): Mutable state, most fixtures
- `session`: Expensive setup (e.g., database engine)
- `class`/`module`: Rarely needed; use when tests share read-only setup

Autouse fixtures:
- Use `autouse=True` when a fixture should apply to all tests in a scope without explicit request
- Commonly used for auth overrides, cleanup, or environment setup

```python
@pytest.fixture(autouse=True)
def patch_user() -> Generator[None]:
    """
    Override auth for all tests in this module.
    """
    app.dependency_overrides[verify_firebase_token] = lambda: fake_user()
    yield
    app.dependency_overrides.clear()
```

Fixture return type annotations (Python 3.14+):
```python
from collections.abc import Generator

@pytest.fixture
def client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c
```

Async fixtures (pytest-asyncio 1.3+):

Use `@pytest_asyncio.fixture` for async fixtures. The `loop_scope` parameter controls which event loop the fixture runs in (independent of caching `scope`):

```python
import pytest_asyncio

@pytest_asyncio.fixture
async def async_resource():
    """
    Function-scoped async fixture (default loop_scope='function').
    """
    resource = await create_resource()
    yield resource
    await resource.cleanup()

@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def module_scoped_resource():
    """
    Module-scoped async fixture sharing the module's event loop.
    """
    return await expensive_async_setup()

@pytest_asyncio.fixture(loop_scope="session", scope="module")
async def session_loop_module_cached():
    """
    Runs in session-scoped loop, cached at module level.
    """
    return await setup_shared_resource()
```

Decorator behavior in `asyncio_mode = "auto"`:
- Regular `@pytest.fixture` on async functions is auto-converted to `@pytest_asyncio.fixture`
- Explicit `@pytest_asyncio.fixture` is recommended for clarity and IDE support
- `@pytest.mark.asyncio` on async tests is **unnecessary** and should be omitted

Loop scope compatibility:
- `loop_scope` must be >= `scope` (e.g., session-loop with module-scope is valid, but module-loop with session-scope is not)

Dynamic fixture scope (advanced):
```python
def determine_scope(fixture_name: str, config: pytest.Config) -> str:
    """
    Dynamically determine fixture scope based on CLI options.
    """
    if config.getoption("--keep-containers", None):
        return "session"
    return "function"

@pytest.fixture(scope=determine_scope)
def docker_container():
    yield spawn_container()
```

Test Helpers (`tests/helpers/`)

Organize reusable test utilities in `tests/helpers/`. Each module should have a focused responsibility:

| Module | Purpose |
|--------|---------|
| `assertions.py` | Response assertion helpers (`assert_error_response`, `assert_validation_error`) |
| `auth.py` | Auth fixtures, fake users, dependency override context managers |
| `clients.py` | TestClient context manager with Firebase/logging patches |
| `profiles.py` | Profile factory functions (`make_profile`, `make_profile_create`, `make_profile_payload_dict`) |
| `starlette_utils.py` | Minimal Starlette app builders for isolated middleware tests |

Factory function patterns:
```python
# tests/helpers/profiles.py
from datetime import UTC, datetime

from app.models.profile import Profile, ProfileCreate, ProfileUpdate


def make_profile_create(
    firstname: str = "John",
    lastname: str = "Doe",
    email: str = "john@example.com",
    phone_number: str = "+1234567890",
    marketing: bool = True,
    terms: bool = True,
) -> ProfileCreate:
    """
    Factory for ProfileCreate with sensible defaults.
    """
    return ProfileCreate(
        firstname=firstname,
        lastname=lastname,
        email=email,
        phone_number=phone_number,
        marketing=marketing,
        terms=terms,
    )


def make_profile(
    user_id: str = "test-user-123",
    **kwargs: object,
) -> Profile:
    """
    Create a Profile instance for testing.
    """
    now = datetime.now(UTC)
    base = {
        "firstname": "John",
        "lastname": "Doe",
        "email": "john@example.com",
        "phone_number": "+1234567890",
        "marketing": True,
        "terms": True,
        "created_at": now,
        "updated_at": now,
    }
    return Profile(id=user_id, **{**base, **kwargs})


def make_profile_update(**kwargs: object) -> ProfileUpdate:
    """
    Factory for ProfileUpdate with only the provided fields.
    """
    return ProfileUpdate(**kwargs)

def make_profile_payload_dict(
    *,
    overrides: dict[str, object] | None = None,
    omit: list[str] | None = None,
) -> dict[str, object]:
    """
    Build a plain dict payload for POST/PUT requests.

    Use `overrides` to change values and `omit` to drop specific keys to test validation errors.
    """
    payload: dict[str, object] = {
        "firstname": "John",
        "lastname": "Doe",
        "email": "john@example.com",
        "phone_number": "+1234567890",
        "marketing": True,
        "terms": True,
    }
    if overrides:
        payload.update(overrides)
    if omit:
        for key in omit:
            payload.pop(key, None)
    return payload
```

Assertion helpers (`tests/helpers/assertions.py`):
```python
from httpx import Response


def assert_error_response(response: Response, expected_status: int) -> dict:
    """
    Assert response matches ErrorResponse schema.

    Args:
        response: The HTTP response to validate.
        expected_status: Expected HTTP status code.

    Returns:
        The parsed JSON body for further assertions.
    """
    assert response.status_code == expected_status
    body = response.json()
    assert "detail" in body, f"Missing 'detail': {body}"
    assert isinstance(body["detail"], str)
    return body


def assert_validation_error(response: Response, field: str) -> dict:
    """
    Assert response is a 422 validation error mentioning the specified field.

    Args:
        response: The HTTP response to validate.
        field: Field name expected to be mentioned in validation errors.

    Returns:
        The parsed JSON body for further assertions.
    """
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    errors = body["detail"]
    assert isinstance(errors, list), f"Expected list of errors: {errors}"
    field_mentioned = any(field in str(err.get("loc", [])) for err in errors)
    assert field_mentioned, f"Field '{field}' not found in validation errors: {errors}"
    return body
```

Usage:
```python
from tests.helpers.assertions import assert_error_response, assert_validation_error

def test_returns_404_when_not_found(client: TestClient, with_fake_user: None) -> None:
    response = client.get("/profile/")
    assert_error_response(response, 404)

def test_returns_422_for_invalid_email(client: TestClient, with_fake_user: None) -> None:
    response = client.post("/profile/", json={"email": "invalid"})
    assert_validation_error(response, "email")
```

Context manager for auth overrides:
```python
# tests/helpers/auth.py
from collections.abc import Callable, Generator
from contextlib import contextmanager

from app.auth.firebase import FirebaseUser, verify_firebase_token
from app.main import app


def make_fake_user(
    uid: str = "test-user-123",
    email: str = "test@example.com",
    verified: bool = True,
) -> FirebaseUser:
    """
    Factory for a fake FirebaseUser.
    """
    return FirebaseUser(uid=uid, email=email, email_verified=verified)


@contextmanager
def override_current_user(user_factory: Callable[[], FirebaseUser]) -> Generator[None]:
    """
    Temporarily override the auth dependency to yield a fake user.

    Usage:
        with override_current_user(lambda: make_fake_user()):
            ... perform client calls ...
    """

    def _override() -> FirebaseUser:
        return user_factory()

    app.dependency_overrides[verify_firebase_token] = _override
    try:
        yield
    finally:
        app.dependency_overrides.clear()
```

Test Mocks (`tests/mocks/`)

Organize mock objects and stub factories in `tests/mocks/`. Use Protocol types for type-safe mocking:

| Module | Purpose |
|--------|---------|
| `firebase.py` | Firebase auth mocks, token verification patches |
| `firestore.py` | Fake Firestore client, collections, documents, transactions for unit tests |
| `http.py` | HTTP client mock helpers (pytest-httpx wrappers) |
| `services.py` | Service layer stubs and mock factories |

Mock patterns:
```python
# tests/mocks/services.py
from unittest.mock import AsyncMock

from app.models.profile import Profile
from app.services.profile import ProfileService
from tests.helpers.profiles import make_profile


def create_mock_profile_service(profile: Profile | None = None) -> AsyncMock:
    """
    Create a mock ProfileService with pre-configured return values.

    Args:
        profile: Optional profile to return from service methods.
                 If None, uses make_profile() with defaults.

    Returns:
        AsyncMock configured with ProfileService spec.
    """
    mock = AsyncMock(spec=ProfileService)
    default_profile = profile or make_profile()
    mock.get_profile.return_value = default_profile
    mock.create_profile.return_value = default_profile
    mock.update_profile.return_value = default_profile
    mock.delete_profile.return_value = default_profile
    return mock


def create_mock_profile_service_not_found() -> AsyncMock:
    """
    Create a mock ProfileService that returns None for get_profile.
    """
    mock = AsyncMock(spec=ProfileService)
    mock.get_profile.return_value = None
    return mock
```

Protocol pattern for type-safe mocks:
```python
# tests/mocks/http.py
from typing import Protocol

class HTTPXMock(Protocol):
    """
    Minimal protocol for pytest-httpx fixture type hints.
    """

    def add_response(self, *, method: str, url: str, json: dict | None = None, status_code: int = 200) -> None: ...

def add_ok_response(httpx_mock: HTTPXMock, url: str, json: dict | None = None) -> None:
    httpx_mock.add_response(method="GET", url=url, json=json or {"ok": True}, status_code=200)

# Usage in tests:
mock_service = AsyncMock(spec=ProfileService)
mock_service.create_profile.return_value = make_profile()
app.dependency_overrides[get_profile_service] = lambda: mock_service
```

Fake Firestore client for service unit tests (`tests/mocks/firestore.py`):
```python
# tests/mocks/firestore.py - comprehensive fake Firestore for unit tests
class FakeDocumentSnapshot:
    """
    Fake Firestore document snapshot.
    """

    def __init__(self, data: dict[str, Any] | None, doc_id: str = "test-id") -> None:
        self._data = data
        self.id = doc_id
        self.exists = data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return self._data


class FakeDocumentReference:
    """
    Fake Firestore document reference with async CRUD methods.
    """

    def __init__(self, store: dict[str, dict[str, Any]], doc_id: str) -> None:
        self._store = store
        self.id = doc_id

    async def get(self) -> FakeDocumentSnapshot:
        data = self._store.get(self.id)
        return FakeDocumentSnapshot(data, self.id)

    async def set(self, data: dict[str, Any]) -> None:
        self._store[self.id] = data


class FakeCollection:
    def __init__(self, store: dict[str, dict[str, Any]]) -> None:
        self._store = store

    def document(self, doc_id: str) -> FakeDocumentReference:
        return FakeDocumentReference(self._store, doc_id)


class FakeAsyncClient:
    """
    Fake async Firestore client for unit tests.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    def collection(self, name: str) -> FakeCollection:
        return FakeCollection(self._store)

    def transaction(self) -> FakeTransaction:
        return FakeTransaction(self._store)

    def clear(self) -> None:
        self._store.clear()
```

Usage in service unit tests:
```python
# tests/unit/services/test_profile.py
from pytest_mock import MockerFixture
from tests.mocks.firestore import FakeAsyncClient

@pytest.fixture
def fake_db(mocker: MockerFixture) -> FakeAsyncClient:
    """
    Patch Firestore client with fake.
    """
    db = FakeAsyncClient()
    mocker.patch("app.services.profile.get_async_firestore_client", return_value=db)
    return db

class TestProfileServiceGetProfile:
    async def test_returns_profile_when_exists(self, fake_db: FakeAsyncClient) -> None:
        fake_db._store["user-123"] = _make_profile_data(user_id="user-123")

        service = ProfileService()
        profile = await service.get_profile("user-123")

        assert profile.id == "user-123"
```

This pattern allows testing service logic without actual Firestore calls while maintaining transaction semantics. Use `pytest-mock` (`mocker` fixture) for cleaner patching.

Firebase mock helpers:
```python
# tests/mocks/firebase.py
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

    monkeypatch.setattr(auth_mod, "get_firebase_app", lambda: MagicMock())


def patch_router_verify_to_raise(monkeypatch: MonkeyPatch, exc: Exception) -> None:
    """
    Patch verify_firebase_token to raise the provided exception.

    Useful in integration tests to simulate invalid/revoked tokens quickly.
    """
    import app.auth.firebase as firebase_auth

    def _raise(*args: object, **kwargs: object) -> None:
        raise exc

    monkeypatch.setattr(firebase_auth, "verify_firebase_token", _raise)
```

TestClient context manager helper (`tests/helpers/clients.py`):
```python
# tests/helpers/clients.py
from collections.abc import Generator
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


@contextmanager
def test_client() -> Generator[TestClient]:
    """
    Context-managed TestClient with Firebase/logging init patched.

    Prefer using the shared `client` fixture from tests/conftest.py in most tests.
    """
    with (
        patch("app.main.initialize_firebase"),
        patch("app.main.setup_logging"),
        patch("app.main.close_async_firestore_client"),
        TestClient(app) as c,
    ):
        yield c
```

Monkeypatch patterns for settings:
```python
def test_production_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "false")
    get_settings.cache_clear()  # Clear cached settings to pick up new env
    # ... test code ...
```

Isolated Middleware Testing

Test middleware in isolation using minimal Starlette apps. Use `tests/helpers/starlette_utils.py`:

```python
# tests/helpers/starlette_utils.py
from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any

from starlette.applications import Starlette

RouteHandler = Callable[..., Awaitable[Any]]
MiddlewareSpec = tuple[type, dict[str, Any]]


def build_starlette_app(
    routes: Sequence[tuple[str, RouteHandler, Sequence[str]]],
    middleware: Iterable[MiddlewareSpec] | None = None,
) -> Starlette:
    """
    Build a minimal Starlette app for tests.

    Parameters:
        routes: Tuples of (path, handler, methods).
        middleware: Optional iterable of (MiddlewareClass, kwargs dict).
    """
    app = Starlette()
    for path, handler, methods in routes:
        app.add_route(path, handler, methods=list(methods))
    if middleware:
        for mw_cls, mw_kwargs in middleware:
            app.add_middleware(mw_cls, **mw_kwargs)
    return app
```

Usage in tests:
```python
from starlette.testclient import TestClient
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.middleware import SecurityHeadersMiddleware
from tests.helpers.starlette_utils import build_starlette_app


def _create_app() -> Starlette:
    async def ping(request: Request) -> PlainTextResponse:
        return PlainTextResponse("pong")

    return build_starlette_app(
        routes=[("/ping", ping, ["GET"])],
        middleware=[(SecurityHeadersMiddleware, {})],
    )


class TestSecurityHeaders:
    def test_x_frame_options_deny(self) -> None:
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert response.status_code == 200
            assert response.headers.get("x-frame-options") == "DENY"

    def test_x_content_type_options_nosniff(self) -> None:
        with TestClient(_create_app()) as client:
            response = client.get("/ping")
            assert response.headers.get("x-content-type-options") == "nosniff"
```

Parameterized Testing

Use `@pytest.mark.parametrize` for data-driven tests. This reduces duplication and makes edge cases explicit:

```python
@pytest.mark.parametrize(
    "missing_field",
    ["firstname", "lastname", "email", "phone_number", "terms"],
)
def test_create_profile_missing_required_field_returns_422(
    client: TestClient, with_fake_user: None, missing_field: str
) -> None:
    payload = make_profile_payload_dict(omit=[missing_field])
    res = client.post("/profile/", json=payload)
    assert res.status_code == 422
    body = res.json()
    assert any(missing_field in str(err.get("loc", [])) for err in body["detail"])
```

Multiple parameters - combine with nested parametrize:
```python
@pytest.mark.parametrize("field", ["marketing", "terms"])
@pytest.mark.parametrize("bad_value", [{}, []])
def test_create_profile_non_boolean_fields_return_422(
    client: TestClient, with_fake_user: None, field: str, bad_value: object
) -> None:
    payload = make_profile_payload_dict(overrides={field: bad_value})
    res = client.post("/profile/", json=payload)
    assert res.status_code == 422
```

Mark individual parameter sets with pytest.param:
```python
@pytest.mark.parametrize(
    ("n", "expected"),
    [
        (1, 2),
        pytest.param(1, 3, marks=pytest.mark.xfail(reason="known bug")),
        pytest.param(0, 1, id="zero-case"),  # Custom ID for clarity
        pytest.param(-1, 0, marks=[pytest.mark.slow, pytest.mark.edge_case]),  # Multiple marks
    ],
)
def test_increment(n: int, expected: int) -> None:
    assert n + 1 == expected
```

Note: Using marks directly on parametrize values (e.g., `pytest.mark.xfail((6, 36))`) is deprecated. Always use `pytest.param()` to apply marks to parameter sets.

Persistence Verification for Mutating Endpoints

Tests for mutating endpoints (POST/PUT/PATCH) should verify that changes persist, not just that the response contains expected values. Use a corresponding GET endpoint to verify persistence:

```python
def test_updates_first_name(self, client: TestClient) -> None:
    """
    Update first_name and verify persistence.
    """
    response = client.put(f"{BASE_URL}/", json={"firstname": "Updated"})

    assert response.status_code == 200
    assert response.json()["firstname"] == "Updated"

    # Verify persistence via GET
    get_response = client.get(f"{BASE_URL}/")
    assert get_response.json()["firstname"] == "Updated"
```

Why this matters: Tests that only assert on the response will pass even if database commit is missing from the route implementation.

When persistence verification is essential:
- **PUT/PATCH** - Always verify; missing commit is a common bug that response-only tests won't catch
- **POST** - Verify when the response could be constructed before commit, or when related records are created
- **DELETE** - Verify the resource is gone via GET (expect 404)

HTTP Response Headers in Tests

Use lowercase header names in assertions (HTTP/2 compliance, Starlette normalizes to lowercase):

```python
# Correct - lowercase
assert response.headers.get("x-frame-options") == "DENY"
assert response.headers.get("www-authenticate") == "Bearer"

# Avoid - uppercase (may work but inconsistent)
assert response.headers.get("X-Frame-Options") == "DENY"
```

Warnings

Check for pytest warnings and fix them. Run with `-W default` to see warnings or `-W error` to treat them as errors:

```bash
just test -- -W default 2>&1 | grep -A 20 "warnings summary"  # View warnings
just test -- -W error                                          # Fail on warnings
```

Common warning sources:
- **DeprecationWarning**: Using deprecated APIs. Update to current API versions.
- **PytestUnraisedExceptionWarning**: Exception not properly handled in async code.

Run commands (repo root)
1) `just test` (unit + integration, CI-compatible)
2) `just test-unit` (unit tests only)
3) `just test-integration` (integration tests only)
4) `just test-e2e` (E2E tests, requires `just emulators` running)
5) `just test-all` (all tests including E2E)
6) `just cov` (coverage report to `htmlcov/`)
7) Optional: `uv run -m pytest` if not using `just`
8) The `pytest-httpx` plugin is auto-discovered by pytest; import is not required for activation.
9) pytest-asyncio is configured in `pyproject.toml` with:
   - `asyncio_mode = "auto"` - async tests/fixtures auto-detected
   - `asyncio_default_fixture_loop_scope = "function"` - async fixtures run in function-scoped loop
   - `asyncio_default_test_loop_scope = "function"` - async tests run in function-scoped loop
   - **No `@pytest.mark.asyncio` decorator needed** (auto mode handles detection)

Writing tests (examples)

1) Basic API test (sync with TestClient)
- Covers happy path, asserts shape and codes; runs lifespan automatically when using a context manager.

```python
from fastapi.testclient import TestClient
from app.main import app

def test_root_ok() -> None:
	with TestClient(app) as client:
		r = client.get("/")
		assert r.status_code == 200
		body = r.json()
		assert body["message"] == "Hello World"
		assert body["docs"] == "/api-docs"
```

2) Async test (true async using httpx AsyncClient)
- Useful for `async` flows or when you need `await` behavior. Use `ASGITransport` for ASGI apps.
- No `@pytest.mark.asyncio` needed with `asyncio_mode = "auto"`.

```python
import httpx
from app.main import app

async def test_health_async() -> None:
	transport = httpx.ASGITransport(app=app)
	async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
		r = await ac.get("/health")
		assert r.status_code == 200
		assert r.json() == {"status": "healthy"}
```

3) Overriding dependencies (auth)
- For routes protected by Firebase auth, override the dependency so no real token verification happens.

```python
from fastapi.testclient import TestClient
from app.main import app
from app.auth.firebase import FirebaseUser, verify_firebase_token

def _fake_user() -> FirebaseUser:
	return FirebaseUser(uid="test-uid", email="user@example.com", email_verified=True)

def test_profile_get_with_fake_auth() -> None:
	# Override verify_firebase_token to return a fake user
	app.dependency_overrides[verify_firebase_token] = lambda: _fake_user()
	try:
		with TestClient(app) as client:
			r = client.get("/profile/")
			# Depending on service state, this may be 404 if profile is missing.
			assert r.status_code in (200, 404)
	finally:
		app.dependency_overrides.clear()
```

4) Asserting errors and validation
- Raise/propagate HTTP errors with clear `detail` and correct codes; assert both.

```python
from fastapi.testclient import TestClient
from app.main import app

def test_unauthorized_without_bearer() -> None:
	with TestClient(app) as client:
		r = client.get("/profile/")  # missing Authorization header
		assert r.status_code == 403 or r.status_code == 401  # depends on security scheme behavior

def test_profile_not_found_details() -> None:
	# Fake auth to pass security, then expect a not-found when no profile exists
	from app.auth.firebase import FirebaseUser, verify_firebase_token

	app.dependency_overrides[verify_firebase_token] = lambda: FirebaseUser(uid="no-profile-uid")
	try:
		with TestClient(app) as client:
			r = client.get("/profile/")
			if r.status_code == 404:
				assert r.json()["detail"] == "Profile not found"
	finally:
		app.dependency_overrides.clear()
```

5) Lifespan events
- When using `with TestClient(app)`, startup/shutdown (lifespan) is executed automatically. Prefer a fixture that yields the client.

```python
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def client() -> Generator[TestClient]:
	with TestClient(app) as c:
		yield c

def test_root_with_fixture(client: TestClient) -> None:
	assert client.get("/").status_code == 200
```

6) Headers and security
- Assert security headers set by middleware and CORS behavior when applicable.

```python
from fastapi.testclient import TestClient
from app.main import app

def test_security_headers() -> None:
	with TestClient(app) as client:
		r = client.get("/")
		# Use lowercase header names (HTTP/2 compliant, Starlette normalizes)
		assert r.headers.get("x-frame-options") == "DENY"
		assert r.headers.get("referrer-policy") == "same-origin"
```

7) Mocking outbound HTTP with pytest-httpx
- Use the `httpx_mock` fixture (provided by pytest-httpx) to intercept external requests made with `httpx`. Provide deterministic responses and avoid network.
- The fixture is auto-injected; no import needed. Type hint with `pytest_httpx.HTTPXMock` if desired.

```python
import httpx
from pytest_httpx import HTTPXMock

def test_outbound_call(httpx_mock: HTTPXMock) -> None:
	# Arrange a mocked HTTP response
	httpx_mock.add_response(
		method="GET",
		url="https://example.com/api/status",
		json={"ok": True},
		status_code=200,
	)

	# Exercise code under test that internally calls httpx.get(...)
	resp = httpx.get("https://example.com/api/status")

	# Assert
	assert resp.status_code == 200
	assert resp.json() == {"ok": True}
```

pytest-httpx advanced patterns:
```python
# Dynamic callback response
async def test_dynamic_response(httpx_mock: HTTPXMock) -> None:
    async def simulate_latency(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.1)
        return httpx.Response(status_code=200, json={"url": str(request.url)})

    httpx_mock.add_callback(simulate_latency)
    async with httpx.AsyncClient() as client:
        response = await client.get("https://api.example.com/data")
        assert response.json()["url"] == "https://api.example.com/data"
```

Asserting all mocked responses were used:
```python
# By default, pytest-httpx asserts all registered responses are used
# Disable per-test with the httpx_mock marker:
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_optional_call(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://optional.example.com")
    # Test passes even if the mocked URL is never called
```

pytest-httpx assertion methods:
```python
def test_request_assertions(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://api.example.com/data")
    
    with httpx.Client() as client:
        client.get("https://api.example.com/data")
    
    # Assert request was made
    httpx_mock.assert_called()
    httpx_mock.assert_called_once()
    
    # Get request for detailed inspection
    request = httpx_mock.get_request()
    assert request.url == "https://api.example.com/data"
    assert request.method == "GET"
```

8) Simulating HTTP exceptions with pytest-httpx
- Use `add_exception` to test error handling for timeouts, connection errors, etc.

```python
import httpx
import pytest
from pytest_httpx import HTTPXMock

def test_timeout_handling(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ReadTimeout("Connection timed out"))
    with pytest.raises(httpx.ReadTimeout):
        with httpx.Client() as client:
            client.get("https://api.example.com/data")
```

9) Authentication fixture pattern
- Create reusable fixtures for authenticated/unauthenticated states.
- Use helper modules for factory functions and context managers.

```python
# tests/conftest.py
from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from app.auth.firebase import FirebaseUser
from app.main import app
from tests.helpers.auth import make_fake_user, override_current_user

@pytest.fixture
def fake_user() -> FirebaseUser:
    """
    A simple fake FirebaseUser for auth overrides/tests.
    """
    return make_fake_user()

@pytest.fixture
def with_fake_user(fake_user: FirebaseUser) -> Generator[None]:
    """
    Override router current user for the duration of a test.
    """
    with override_current_user(lambda: fake_user):
        yield
```

Usage in tests - compose fixtures:
```python
class TestProfileEndpoint:
    def test_returns_profile(self, client: TestClient, with_fake_user: None) -> None:
        """
        Authenticated request returns profile.
        """
        response = client.get("/profile/")
        assert response.status_code in (200, 404)

    def test_returns_401_without_auth(self, client: TestClient) -> None:
        """
        Unauthenticated request returns 401.
        """
        response = client.get("/profile/")
        assert response.status_code == 401
        assert response.headers.get("www-authenticate") == "Bearer"
```

Integration tests with mock_profile_service fixture (preferred pattern):
```python
# tests/integration/routers/test_profile.py
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.exceptions import ProfileAlreadyExistsError, ProfileNotFoundError
from tests.helpers.profiles import make_profile, make_profile_payload_dict

BASE_URL = "/profile"


class TestCreateProfile:
    """
    Tests for POST /profile/.
    """

    def test_returns_201_on_success(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify successful profile creation returns 201.
        """
        mock_profile_service.create_profile.return_value = make_profile()

        response = client.post(f"{BASE_URL}/", json=make_profile_payload_dict())

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        mock_profile_service.create_profile.assert_awaited_once()

    def test_returns_409_when_duplicate(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify duplicate profile returns 409 Conflict.
        """
        mock_profile_service.create_profile.side_effect = ProfileAlreadyExistsError()

        response = client.post(f"{BASE_URL}/", json=make_profile_payload_dict())

        assert response.status_code == 409
        assert response.json()["detail"] == "Profile already exists"

    def test_returns_401_without_auth(
        self,
        client: TestClient,
        mock_profile_service: AsyncMock,
    ) -> None:
        """
        Verify unauthenticated request returns 401.
        """
        response = client.post(f"{BASE_URL}/", json=make_profile_payload_dict())

        assert response.status_code == 401

    @pytest.mark.parametrize(
        "missing_field",
        ["firstname", "lastname", "email", "phone_number", "terms"],
    )
    def test_returns_422_for_missing_fields(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_profile_service: AsyncMock,
        missing_field: str,
    ) -> None:
        """
        Verify missing required fields return 422.
        """
        payload = make_profile_payload_dict(omit=[missing_field])

        response = client.post(f"{BASE_URL}/", json=payload)

        assert response.status_code == 422
```

Override service dependencies:
```python
from unittest.mock import AsyncMock
from app.dependencies import get_profile_service
from app.services.profile import ProfileService

def test_create_profile_success(client: TestClient, with_fake_user: None) -> None:
    """
    Test with mocked service layer.
    """
    mock_service = AsyncMock(spec=ProfileService)
    mock_service.create_profile.return_value = make_profile()

    app.dependency_overrides[get_profile_service] = lambda: mock_service
    try:
        payload = make_profile_payload_dict()
        res = client.post("/profile/", json=payload)
        assert res.status_code == 201
    finally:
        app.dependency_overrides.pop(get_profile_service, None)
```

Dependency override cleanup strategies:

```python
# Option 1: try/finally (preferred for single overrides)
app.dependency_overrides[get_profile_service] = lambda: mock_service
try:
    # test code
finally:
    app.dependency_overrides.pop(get_profile_service, None)

# Option 2: Clear all overrides (when multiple were set)
app.dependency_overrides[dep1] = lambda: mock1
app.dependency_overrides[dep2] = lambda: mock2
try:
    # test code
finally:
    app.dependency_overrides.clear()

# Option 3: Autouse fixture for module-wide override (see Autouse fixtures section)
```

Common pitfalls (and fixes)
- Not clearing `app.dependency_overrides` → tests influence each other. Use `try/finally` or context manager.
- Mixing sync TestClient inside async tests → use `httpx.AsyncClient` or keep tests sync.
- Creating `TestClient(app)` without context manager → lifespan may not run; use fixture with `with`.
- Real Firebase/GCP calls in tests → must be mocked.
- Weak assertions → assert status, body shape, and headers.
- Real outbound HTTP not mocked → use `pytest-httpx`.
- Using `@pytest.mark.asyncio` when not needed → with `asyncio_mode="auto"`, remove the decorator.
- Forgetting to clear cached settings → call `get_settings.cache_clear()` after `monkeypatch.setenv()`.
- Applying marks to fixtures → deprecated in pytest 8+; use fixture dependencies instead.

Anti-Patterns

Avoid: Test code in production
```python
# BAD - Don't do this in app/
if os.environ.get("TESTING"):
    return mock_response
```

Avoid: Module-level client
```python
# BAD - State leaks between tests
client = TestClient(app)

# GOOD - Use fixtures
def test_something(client: TestClient) -> None: ...
```

Avoid: Real network calls
```python
# BAD
response = httpx.get("https://api.external.com/data")

# GOOD
def test_call(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://api.external.com/data", json={})
```

Avoid: Hardcoded secrets
```python
# BAD
api_key = "sk-real-secret-key-12345"

# GOOD
api_key = "test-api-key"
```

Avoid: Manually running async fixtures in sync tests
```python
# BAD - deprecated pattern
@pytest.fixture
async def unawaited_fixture():
    return 1

def test_foo(unawaited_fixture):
    assert 1 == asyncio.run(unawaited_fixture)

# GOOD - use async test or sync fixture
async def test_foo(unawaited_fixture):  # with asyncio_mode="auto"
    assert unawaited_fixture == 1
```

Avoid: Direct fixture function calls
```python
# BAD - deprecated, raises warning
@pytest.fixture
def cell():
    return ...

@pytest.fixture
def full_cell():
    cell = cell()  # Direct call
    cell.make_full()
    return cell

# GOOD - request fixture as parameter
@pytest.fixture
def full_cell(cell):  # Dependency injection
    cell.make_full()
    return cell
```

Avoid: Marks applied to fixtures (deprecated in pytest 8+)
```python
# BAD - raises PytestWarning, will become an error
@pytest.mark.usefixtures("clean_database")
@pytest.fixture
def user():
    return User()

# GOOD - request fixture as dependency
@pytest.fixture
def user(clean_database):  # Dependency injection
    return User()
```

Quality gates
- Types: `just typing`
- Lint/format: `just lint`
- Tests: `just test` (or `just cov` for coverage)

When API changes
- Update related tests and ensure router `response_model`, `status_code`, and examples match actual responses.
- Keep OpenAPI consistent (FastAPI generates it automatically). If you introduce a shared error schema, reuse it across endpoints and assert it in tests.

Notes
- These conventions align with FastAPI’s testing guidance (TestClient, dependency overrides, async tests, and lifespan handling) and this repo’s tooling (just, uv, Ruff, ty).
