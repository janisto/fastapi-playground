---
name: pytest-testing
description: Guide for writing pytest tests following this project's patterns including fixtures, mocking, and test organization.
---
# Pytest Testing

Use this skill when writing tests for this FastAPI application. Follow these patterns for consistency.

## Test Organization

| Category | Path | Focus |
|----------|------|-------|
| Unit | `tests/unit/` | Models, config, services, middleware |
| Integration | `tests/integration/` | API routes with mocked services |
| E2E | `tests/e2e/` | Real Firebase emulator tests |

Mirror the `app/` structure in test directories.

## Integration Test Pattern

Integration tests use the FastAPI TestClient with mocked services:

```python
"""
Integration tests for resource endpoints.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.exceptions import ResourceAlreadyExistsError, ResourceNotFoundError
from tests.helpers.resources import make_resource, make_resource_payload_dict

BASE_URL = "/resource"


class TestCreateResource:
    """
    Tests for POST /resource/.
    """

    def test_returns_201_on_success(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_resource_service: AsyncMock,
    ) -> None:
        """
        Verify successful resource creation returns 201.
        """
        mock_resource_service.create_resource.return_value = make_resource()

        response = client.post(f"{BASE_URL}/", json=make_resource_payload_dict())

        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        mock_resource_service.create_resource.assert_awaited_once()

    def test_returns_409_when_duplicate(
        self,
        client: TestClient,
        with_fake_user: None,
        mock_resource_service: AsyncMock,
    ) -> None:
        """
        Verify duplicate resource returns 409 Conflict.
        """
        mock_resource_service.create_resource.side_effect = ResourceAlreadyExistsError()

        response = client.post(f"{BASE_URL}/", json=make_resource_payload_dict())

        assert response.status_code == 409
        assert response.json()["detail"] == "Resource already exists"

    def test_returns_401_without_auth(
        self,
        client: TestClient,
        mock_resource_service: AsyncMock,
    ) -> None:
        """
        Verify unauthenticated request returns 401.
        """
        response = client.post(f"{BASE_URL}/", json=make_resource_payload_dict())

        assert response.status_code == 401
```

## Fixtures

Use fixtures from `tests/conftest.py`:
- `client` - TestClient with Firebase/logging patched
- `fake_user` - Simple fake FirebaseUser
- `with_fake_user` - Override auth dependency

Add service mock fixtures in integration `conftest.py`:

```python
@pytest.fixture
def mock_resource_service() -> AsyncMock:
    """
    Mocked ResourceService for integration tests.
    """
    return AsyncMock(spec=ResourceService)
```

## Helper Functions

Create factory functions in `tests/helpers/`:

```python
# tests/helpers/resources.py
from datetime import UTC, datetime

from app.models.resource import Resource, ResourceCreate


def make_resource(
    resource_id: str = "test-resource-123",
    **kwargs: object,
) -> Resource:
    """
    Create a Resource instance for testing.
    """
    now = datetime.now(UTC)
    base = {
        "name": "Test Resource",
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    return Resource(id=resource_id, **{**base, **kwargs})


def make_resource_payload_dict(
    *,
    overrides: dict[str, object] | None = None,
    omit: list[str] | None = None,
) -> dict[str, object]:
    """
    Build a plain dict payload for POST/PUT requests.
    """
    payload: dict[str, object] = {
        "name": "Test Resource",
        "active": True,
    }
    if overrides:
        payload.update(overrides)
    if omit:
        for key in omit:
            payload.pop(key, None)
    return payload
```

## Parametrized Tests

Use `@pytest.mark.parametrize` for data-driven tests:

```python
@pytest.mark.parametrize(
    "missing_field",
    ["name", "email", "phone_number"],
)
def test_returns_422_for_missing_fields(
    self,
    client: TestClient,
    with_fake_user: None,
    missing_field: str,
) -> None:
    """
    Verify missing required fields return 422.
    """
    payload = make_resource_payload_dict(omit=[missing_field])

    response = client.post(f"{BASE_URL}/", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert any(missing_field in str(err.get("loc", [])) for err in body["detail"])
```

## Async Tests

With `asyncio_mode = "auto"` in pyproject.toml, no decorator is needed:

```python
async def test_async_operation() -> None:
    """
    Async test runs automatically without @pytest.mark.asyncio.
    """
    result = await some_async_function()
    assert result is not None
```

## Mocking Patterns

Use `pytest-mock` (`mocker` fixture) for patching:

```python
def test_with_mock(mocker: MockerFixture) -> None:
    mock_client = mocker.patch("app.services.resource.get_async_firestore_client")
    mock_client.return_value = FakeAsyncClient()
    # ... test code
```

Use `monkeypatch` for environment variables:

```python
def test_with_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEBUG", "true")
    get_settings.cache_clear()
    # ... test code
```

## Test Naming

Pattern: `test_<what>_<condition/scenario>`

```python
def test_create_resource_returns_201_on_success() -> None: ...
def test_get_resource_returns_404_when_not_found() -> None: ...
def test_update_resource_with_invalid_email_returns_422() -> None: ...
```

## URL Conventions

Always use trailing slashes in tests to match routes:

```python
# Correct
response = client.get("/resource/")

# Wrong - may cause 307 redirect
response = client.get("/resource")
```

## Running Tests

```bash
just test               # Unit + integration (CI-compatible)
just test-unit          # Unit tests only
just test-integration   # Integration tests only
just test-e2e           # E2E tests (requires: just emulators)
just cov                # Coverage report
```
