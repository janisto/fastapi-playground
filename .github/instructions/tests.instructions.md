---
applyTo: "tests/**"
---

Use these rules for tests under `tests/**` (Python 3.13, FastAPI, pytest, pytest-asyncio). The project uses `httpx` for HTTP clients and `pytest-httpx` for mocking outbound HTTP in tests.

Structure
- Unit tests → `tests/unit/**` (mirror `app/**` modules; pure logic with tight mocks)
- Integration/API tests → `tests/integration/**` (use FastAPI TestClient against the app)
- E2E-style flows → `tests/e2e/**` (narrow happy paths; still mock external services)
- Fixtures and helpers → `tests/conftest.py`, `tests/helpers/**`, `tests/mocks/**`

Conventions
- No real network, files, or Firebase/Google Cloud in unit/integration tests; mock `firebase_admin` and any external I/O.
- Prefer FastAPI patterns from the docs: use `TestClient` for sync-style API tests; use `pytest.mark.asyncio` with `httpx.AsyncClient` for true async cases.
- HTTP client and mocking: use `httpx` in code; stub outbound HTTP with `pytest-httpx` via the `httpx_mock` fixture. Do not hit the real network.
- Override dependencies via `app.dependency_overrides` (e.g., auth/user, database/session). Reset overrides after each test to avoid leakage.
- Aim ≥90% coverage overall; 100% on critical business logic (auth, security, error handling).
- Validate API contracts: assert status codes, JSON shapes, and headers. Keep `response_model` accurate in routers and assert against it.
- Keep Ruff and typing clean: run `just lint` and `just typing`. Avoid `print`; use logger if needed.
- Use realistic but synthetic fixtures. Never log or include secrets/PII in test data.

Comment discipline
- Do not add progress or narrative comments (e.g., "setting up test", "now calling endpoint").
- Keep comments only for complex fixture setup, intricate mocking, race-condition mitigation, or rationale behind unusual assertions.
- Do not duplicate the test name or obvious Given/When/Then steps in comments.
- Remove outdated comments immediately when altering test logic.

Run commands (repo root)
1) `just test` (pass extra pytest args as needed)
2) `just cov` (coverage report to `htmlcov/`)
3) Optional: `uv run -m pytest` if not using `just`
4) The `pytest-httpx` plugin is auto-discovered by pytest; import is not required for activation.

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
- Useful for `async` flows or when you need `await` behavior. See FastAPI docs on async testing.

```python
import pytest
import httpx
from app.main import app

@pytest.mark.asyncio
async def test_health_async() -> None:
	async with httpx.AsyncClient(app=app, base_url="http://testserver") as ac:
		r = await ac.get("/health")
		assert r.status_code == 200
		assert r.json() == {"status": "healthy"}
```

3) Overriding dependencies (auth)
- For routes protected by Firebase auth, override the dependency so no real token verification happens.

```python
from fastapi.testclient import TestClient
from app.main import app
from app.auth.firebase import FirebaseUser

def _fake_user() -> FirebaseUser:  # simple helper
	return FirebaseUser(uid="test-uid", email="user@example.com", email_verified=True)

def override_verify(credentials):  # signature matches dependency param
	return _fake_user()

def test_profile_get_with_fake_auth() -> None:
	# Patch the dependency the router actually uses
	from app.routers.profile import _current_user_dependency
	app.dependency_overrides[_current_user_dependency] = override_verify
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
	from app.routers.profile import _current_user_dependency
	from app.auth.firebase import FirebaseUser

	app.dependency_overrides[_current_user_dependency] = lambda cred: FirebaseUser("no-profile-uid")
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
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
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
		# Examples — adjust to middleware config
		assert r.headers.get("X-Frame-Options") == "DENY"
		assert r.headers.get("Referrer-Policy") == "same-origin"
```

7) Mocking outbound HTTP with pytest-httpx
- Use the `httpx_mock` fixture to intercept external requests made with `httpx`. Provide deterministic responses and avoid network.

```python
import httpx

def test_outbound_call(httpx_mock) -> None:
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

Common pitfalls (and fixes)
- Not clearing `app.dependency_overrides` → tests influence each other. Use `try/finally` or a fixture to clean up.
- Mixing sync TestClient calls inside `@pytest.mark.asyncio` tests → either use `httpx.AsyncClient` or call sync tests without asyncio.
- Creating `TestClient(app)` without a context manager → lifespan may not run; prefer a fixture that uses `with`.
- Real Firebase/GCP calls in tests → must be mocked (e.g., patch `firebase_admin.auth.verify_id_token` or override the auth dependency).
- Weak assertions → assert status, body shape, and headers; for errors, assert `detail` matches.
- Real outbound HTTP not mocked → use `pytest-httpx` (`httpx_mock`) to intercept external requests and keep tests hermetic.

Quality gates
- Types: `just typing`
- Lint/format: `just lint`
- Tests: `just test` (or `just cov` for coverage)

When API changes
- Update related tests and ensure router `response_model`, `status_code`, and examples match actual responses.
- Keep OpenAPI consistent (FastAPI generates it automatically). If you introduce a shared error schema, reuse it across endpoints and assert it in tests.

Notes
- These conventions align with FastAPI’s testing guidance (TestClient, dependency overrides, async tests, and lifespan handling) and this repo’s tooling (just, uv, Ruff, ty).
