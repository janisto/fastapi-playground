---
name: pytest-testing
description: Write or review fastapi-playground tests using pytest, FastAPI TestClient, async tests, dependency overrides, Firestore fakes, Firebase emulators, HTTPX2, coverage, and repository fixtures.
---

# Pytest testing

Read `AGENTS.md`, the implementation under test, `tests/conftest.py`, and neighboring tests before choosing a boundary.

## Choose the narrowest useful test

- Pure models, helpers, services, and isolated middleware belong in `tests/unit/`.
- Composed routing, handlers, middleware order, negotiation, and exception responses belong in `tests/integration/`.
- Real Auth or Firestore SDK behavior belongs in `tests/e2e/` with local Firebase emulators.

Use the shared fixtures and helpers before adding new ones. Override FastAPI dependencies on `fastapi_app`, while HTTP
clients target the exported outer `app` so request IDs and response-wide middleware are exercised. Always clean up
overrides. Do not add production test hooks, environment backdoors, sleeps, or real network access to unit or
integration tests.

Assert observable contracts: exact status, relevant headers, decoded response shape, Problem Details, JSON and CBOR
negotiation, authentication and authorization, body limits, request IDs, stale cursors, and absence of sensitive log
fields. Prefer parametrization for validation matrices and `AsyncMock` assertions for async service calls.

Use `pytest-mock` for call-aware patching, `monkeypatch` for environment isolation, HTTPX2 for HTTP requests, and
`pytest-httpx2` for outbound mocks. With automatic asyncio mode, do not add `pytest.mark.asyncio` to ordinary async
tests.

## Commands

Run the focused file or node first, then the relevant suite:

```bash
just test-unit
just test-integration
just test
just cov
just test-e2e
```

Finish code changes with `just lint`, `just typing`, and `just test`.
